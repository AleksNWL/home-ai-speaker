from __future__ import annotations

import logging
import queue
import threading
import time
from pathlib import Path
from typing import Any

from src.audio import EnergyVad, create_capture, create_playback
from src.config import resolve_path
from src.llm import GeminiClient
from src.skills import SkillRegistry
from src.status import StatusBus
from src.stt import WhisperSTT
from src.tts import PiperTTS
from src.wake import WakeWordDetector

logger = logging.getLogger(__name__)


class SpeakerApp:
    def __init__(self, cfg: dict[str, Any], status: StatusBus | None = None) -> None:
        self.cfg = cfg
        self.status = status or StatusBus()
        audio_cfg = cfg.get("audio", {})
        wake_cfg = cfg.get("wake", {})
        stt_cfg = cfg.get("stt", {})
        tts_cfg = cfg.get("tts", {})
        llm_cfg = cfg.get("llm", {})
        speaker_cfg = cfg.get("speaker", {})

        self.listen_seconds = float(audio_cfg.get("listen_seconds", 6.0))
        self.capture = create_capture(audio_cfg)
        self.playback = create_playback(audio_cfg)
        self.vad = None
        if audio_cfg.get("vad_enabled", True):
            self.vad = EnergyVad(
                threshold=float(audio_cfg.get("vad_rms_threshold", 0.012)),
                silence_ms=int(audio_cfg.get("vad_silence_ms", 900)),
                sample_rate=self.capture.sample_rate,
            )

        model_path = resolve_path(wake_cfg.get("model_path"))
        self.wake = WakeWordDetector(
            model_name=speaker_cfg.get("wake_word", "hey_jarvis"),
            threshold=float(wake_cfg.get("threshold", 0.5)),
            cooldown_seconds=float(wake_cfg.get("cooldown_seconds", 1.5)),
            model_path=str(model_path) if model_path else None,
            sample_rate=self.capture.sample_rate,
        )

        download_root = resolve_path(stt_cfg.get("download_root"))
        self.stt = WhisperSTT(
            model_size=stt_cfg.get("model_size", "base"),
            device=stt_cfg.get("device", "cpu"),
            compute_type=stt_cfg.get("compute_type", "int8"),
            download_root=download_root,
            language=speaker_cfg.get("language", "ru"),
        )

        tts_model = resolve_path(tts_cfg.get("model_path"))
        tts_config = resolve_path(tts_cfg.get("config_path"))
        piper_bin = resolve_path(tts_cfg.get("piper_binary")) or Path(
            tts_cfg.get("piper_binary") or "piper"
        )
        self.tts = PiperTTS(
            model_path=tts_model or "models/piper/missing.onnx",
            config_path=tts_config,
            piper_binary=str(piper_bin),
            speak_rate=float(tts_cfg.get("speak_rate", 1.0)),
        )

        self.skills = SkillRegistry(cfg, on_timer=self._on_timer)
        api_key = (cfg.get("gemini") or {}).get("api_key", "")
        self.llm = GeminiClient(
            api_key=api_key,
            model=llm_cfg.get("model", "gemini-2.0-flash"),
            system_prompt=llm_cfg.get("system_prompt", ""),
            temperature=float(llm_cfg.get("temperature", 0.4)),
            max_output_tokens=int(llm_cfg.get("max_output_tokens", 512)),
        )

        self._stop = threading.Event()
        self._busy = threading.Lock()

    def _on_timer(self, message: str) -> None:
        logger.info("Timer fired: %s", message)
        # Speak asynchronously so we don't block timer thread too long
        threading.Thread(target=self.speak, args=(message,), daemon=True).start()

    def speak(self, text: str) -> None:
        self.status.set_state("speaking", last_reply=text, error="")
        audio, rate = self.tts.synthesize(text)
        self.playback.play(audio, sample_rate=rate)
        self.status.set_state("idle")

    def handle_utterance(self) -> None:
        if not self._busy.acquire(blocking=False):
            logger.info("Busy — ignoring wake")
            return
        try:
            self.status.set_state("listening")
            # Drop buffered pre-wake audio so STT hears the command
            drained = 0
            while True:
                try:
                    self.capture._q.get_nowait()
                    drained += 1
                except queue.Empty:
                    break
            if drained:
                logger.debug("Drained %s pre-roll chunks", drained)
            audio = self.capture.read_utterance(self.listen_seconds, vad=self.vad)
            self.status.set_state("thinking")
            transcript = self.stt.transcribe(audio, sample_rate=self.capture.sample_rate)
            self.status.update(last_transcript=transcript)
            if not transcript:
                self.speak("Не расслышала, повтори пожалуйста.")
                return

            local = self.skills.try_local_rules(transcript)
            if local is not None:
                reply = local
            else:
                try:
                    reply = self.llm.reply(
                        transcript,
                        tools=self.skills.tool_schemas(),
                        dispatch=self.skills.dispatch,
                    )
                except Exception as exc:
                    logger.exception("LLM failed")
                    self.status.update(error=str(exc))
                    reply = f"Ошибка ИИ: {exc}"

            # Track music status for display
            if "сейчас" in reply.lower() and ("play" in transcript.lower() or "музык" in transcript.lower()):
                self.status.update(now_playing=reply)

            self.speak(reply or "Готово.")
        finally:
            self.status.set_state("idle")
            self._busy.release()

    def run(self) -> None:
        logger.info("Speaker starting — wake then listen")
        self.status.set_state("idle")
        self.capture.start()
        wake_count = 0
        pause_wake = threading.Event()

        def gated_chunks():
            for chunk in self.capture.chunks():
                if self._stop.is_set():
                    break
                if pause_wake.is_set():
                    # Drop audio while handling an utterance / speaking
                    continue
                yield chunk

        def session() -> None:
            try:
                pause_wake.set()
                self.handle_utterance()
            finally:
                # Cooldown against false re-triggers from TTS echo
                time.sleep(0.4)
                pause_wake.clear()

        def on_wake() -> None:
            nonlocal wake_count
            if pause_wake.is_set():
                return
            wake_count += 1
            self.status.update(wake_count=wake_count)
            threading.Thread(target=session, daemon=True).start()

        try:
            self.wake.listen_forever(
                gated_chunks(),
                on_wake=on_wake,
                stop_event=self._stop,
            )
        finally:
            self.capture.stop()

    def stop(self) -> None:
        self._stop.set()
        self.playback.stop()
        self.capture.stop()

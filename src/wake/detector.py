from __future__ import annotations

import logging
import time
from typing import Callable

import numpy as np

logger = logging.getLogger(__name__)


class WakeWordDetector:
    """openWakeWord wrapper. Falls back to push-to-talk if models unavailable."""

    def __init__(
        self,
        model_name: str = "hey_jarvis",
        threshold: float = 0.5,
        cooldown_seconds: float = 1.5,
        model_path: str | None = None,
        sample_rate: int = 16000,
    ) -> None:
        self.model_name = model_name
        self.threshold = threshold
        self.cooldown_seconds = cooldown_seconds
        self.model_path = model_path
        self.sample_rate = sample_rate
        self._last_fire = 0.0
        self._oww = None
        self._fallback = False
        self._load()

    def _load(self) -> None:
        try:
            from openwakeword.model import Model

            kwargs: dict = {}
            if self.model_path:
                kwargs["wakeword_models"] = [self.model_path]
            self._oww = Model(**kwargs)
            logger.info("openWakeWord loaded (model=%s)", self.model_name)
        except Exception as exc:
            logger.warning("openWakeWord unavailable (%s) — using Enter-key fallback", exc)
            self._fallback = True

    @property
    def fallback(self) -> bool:
        return self._fallback

    def process_chunk(self, chunk: np.ndarray) -> bool:
        if self._fallback or self._oww is None:
            return False
        now = time.time()
        if now - self._last_fire < self.cooldown_seconds:
            return False

        # openWakeWord expects int16 PCM
        if chunk.dtype != np.int16:
            pcm = np.clip(chunk, -1.0, 1.0)
            pcm = (pcm * 32767).astype(np.int16)
        else:
            pcm = chunk

        scores = self._oww.predict(pcm)
        # scores is dict model_name -> score
        score = 0.0
        if isinstance(scores, dict):
            if self.model_name in scores:
                score = float(scores[self.model_name])
            elif scores:
                score = float(max(scores.values()))
        if score >= self.threshold:
            self._last_fire = now
            logger.info("Wake word detected (score=%.3f)", score)
            return True
        return False

    def listen_forever(
        self,
        chunk_iterator,
        on_wake: Callable[[], None],
        stop_event=None,
    ) -> None:
        if self._fallback:
            print(
                "\n=== Режим без wake-word ===\n"
                "Нажми Enter, скажи команду в микрофон, подожди ответ.\n"
                "Ctrl+C — выход.\n",
                flush=True,
            )
            while stop_event is None or not stop_event.is_set():
                try:
                    input("▶ Enter = слушать: ")
                except EOFError:
                    break
                print("… слушаю", flush=True)
                on_wake()
            return

        for chunk in chunk_iterator:
            if stop_event is not None and stop_event.is_set():
                break
            mono = chunk[:, 0] if getattr(chunk, "ndim", 1) > 1 else chunk.reshape(-1)
            if self.process_chunk(mono):
                on_wake()

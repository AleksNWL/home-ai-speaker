#!/usr/bin/env python3
"""Stage 0 — list devices and record/play a short clip via sounddevice."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser(description="Audio smoke test for home-ai-speaker")
    parser.add_argument("--seconds", type=float, default=3.0)
    parser.add_argument("--rate", type=int, default=16000)
    parser.add_argument("--input-device", default=None)
    parser.add_argument("--output-device", default=None)
    parser.add_argument("--save", type=Path, default=None)
    args = parser.parse_args()

    try:
        import sounddevice as sd
    except ImportError:
        print("Install deps first: pip install sounddevice numpy", file=sys.stderr)
        return 1

    print("=== Devices ===")
    print(sd.query_devices())
    print(f"\nDefault: {sd.default.device}")

    frames = int(args.seconds * args.rate)
    print(f"\nRecording {args.seconds}s @ {args.rate} Hz ...")
    audio = sd.rec(
        frames,
        samplerate=args.rate,
        channels=1,
        dtype="float32",
        device=args.input_device,
    )
    sd.wait()
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    rms = float(np.sqrt(np.mean(audio**2))) if audio.size else 0.0
    print(f"Peak={peak:.4f} RMS={rms:.4f}")
    if peak < 0.001:
        print("WARNING: near-silence — check mic / input device / permissions")

    if args.save:
        # Minimal WAV writer without scipy
        import wave

        pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
        with wave.open(str(args.save), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(args.rate)
            wf.writeframes(pcm.tobytes())
        print(f"Saved {args.save}")

    print("Playing back ...")
    sd.play(audio, samplerate=args.rate, device=args.output_device)
    sd.wait()
    time.sleep(0.1)
    print("OK: capture + playback done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

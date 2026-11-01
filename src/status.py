from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable


@dataclass
class SpeakerStatus:
    state: str = "idle"  # idle | listening | thinking | speaking | playing
    last_transcript: str = ""
    last_reply: str = ""
    now_playing: str = ""
    wake_count: int = 0
    error: str = ""
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class StatusBus:
    """Thread-safe status for orchestrator + display HTTP API."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._status = SpeakerStatus()
        self._listeners: list[Callable[[SpeakerStatus], None]] = []

    def get(self) -> SpeakerStatus:
        with self._lock:
            return SpeakerStatus(**asdict(self._status))

    def update(self, **kwargs: Any) -> SpeakerStatus:
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._status, key):
                    setattr(self._status, key, value)
            self._status.updated_at = time.time()
            snapshot = SpeakerStatus(**asdict(self._status))
        for listener in list(self._listeners):
            try:
                listener(snapshot)
            except Exception:
                pass
        return snapshot

    def set_state(self, state: str, **kwargs: Any) -> SpeakerStatus:
        return self.update(state=state, **kwargs)

    def on_change(self, callback: Callable[[SpeakerStatus], None]) -> None:
        self._listeners.append(callback)

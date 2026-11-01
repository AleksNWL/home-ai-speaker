from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class TimersSkill:
    name = "set_timer"

    def __init__(self, cfg: dict[str, Any], on_fire: Callable[[str], None] | None = None) -> None:
        self.enabled = cfg.get("enabled", True)
        self._on_fire = on_fire
        self._timers: list[threading.Timer] = []

    def tool_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": "Поставить таймер на N секунд или минут",
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {"type": "integer", "description": "Секунды"},
                    "minutes": {"type": "integer", "description": "Минуты"},
                    "label": {"type": "string", "description": "Метка таймера"},
                },
            },
        }

    def run(self, seconds: int | None = None, minutes: int | None = None, label: str = "таймер", **_: Any) -> str:
        if not self.enabled:
            return "Таймеры выключены."
        total = int(seconds or 0) + int(minutes or 0) * 60
        if total <= 0:
            return "Укажи длительность таймера."
        label = label or "таймер"

        def _fire() -> None:
            msg = f"Таймер «{label}» сработал."
            logger.info(msg)
            if self._on_fire:
                self._on_fire(msg)

        t = threading.Timer(total, _fire)
        t.daemon = True
        t.start()
        self._timers.append(t)
        if total >= 60:
            return f"Таймер «{label}» на {total // 60} мин {total % 60} сек."
        return f"Таймер «{label}» на {total} секунд."

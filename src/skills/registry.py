from __future__ import annotations

import logging
import re
import shutil
import subprocess
from typing import Any, Callable

from .home_assistant import HomeAssistantSkill
from .music import MusicSkill
from .timers import TimersSkill
from .weather import WeatherSkill

logger = logging.getLogger(__name__)


def _set_volume_percent(percent: int) -> str:
    percent = max(0, min(100, int(percent)))
    if shutil.which("amixer"):
        try:
            subprocess.run(
                ["amixer", "-q", "sset", "Master", f"{percent}%"],
                check=False,
                capture_output=True,
            )
            return f"Громкость {percent}%."
        except Exception as exc:
            return f"Не удалось изменить громкость: {exc}"
    return f"amixer не найден; громкость {percent}% не применена."



class SkillRegistry:
    def __init__(self, cfg: dict[str, Any], on_timer: Callable[[str], None] | None = None) -> None:
        skills_cfg = cfg.get("skills", {})
        self.weather = WeatherSkill(skills_cfg.get("weather", {}))
        self.ha = HomeAssistantSkill(
            skills_cfg.get("home_assistant", {}),
            cfg.get("home_assistant", {}),
        )
        self.music = MusicSkill(skills_cfg.get("music", {}))
        self.timers = TimersSkill(skills_cfg.get("timers", {}), on_fire=on_timer)
        self._by_name = {
            self.weather.name: self.weather,
            self.ha.name: self.ha,
            self.music.name: self.music,
            self.timers.name: self.timers,
        }

    def tool_schemas(self) -> list[dict[str, Any]]:
        return [s.tool_schema() for s in self._by_name.values()]

    def dispatch(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        skill = self._by_name.get(name)
        if not skill:
            return f"Неизвестный инструмент: {name}"
        try:
            return skill.run(**(arguments or {}))
        except TypeError as exc:
            logger.exception("bad args for %s", name)
            return f"Неверные аргументы для {name}: {exc}"
        except Exception as exc:
            logger.exception("skill %s failed", name)
            return f"Ошибка навыка {name}: {exc}"

    def try_local_rules(self, text: str) -> str | None:
        """Fast-path for common commands without LLM."""
        t = (text or "").lower().strip()
        if not t:
            return None

        # Volume
        vm = re.search(r"громкост[ьи]\s+(\d{1,3})", t)
        if vm:
            return _set_volume_percent(int(vm.group(1)))
        if "тише" in t:
            return _set_volume_percent(30)
        if "громче" in t:
            return _set_volume_percent(80)

        # Music shortcuts
        if re.search(r"\b(стоп|останови|пауза)\b", t) and re.search(r"\b(музык|песн|трек)\b", t):
            return self.music.run(action="pause")
        if re.search(r"\b(продолж|играй|включи)\b.*\b(музык|песн)\b", t):
            return self.music.run(action="play")
        if t in {"следующий трек", "следующая песня", "дальше"} or (
            re.search(r"\b(следующ|дальше)\b", t) and re.search(r"\b(трек|песн|музык)\b", t)
        ):
            return self.music.run(action="next")

        m = re.search(r"таймер\s+на\s+(\d+)\s*(секунд|секунды|сек|минут|минуты|мин)", t)
        if m:
            n = int(m.group(1))
            unit = m.group(2)
            if unit.startswith("мин"):
                return self.timers.run(minutes=n)
            return self.timers.run(seconds=n)

        if "погод" in t:
            return self.weather.run()

        return None

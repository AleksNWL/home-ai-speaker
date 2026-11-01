from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from src.skills.registry import SkillRegistry
from src.llm.gemini_client import GeminiClient
from src.audio.vad import EnergyVad
import numpy as np


class LocalRulesTests(unittest.TestCase):
    def setUp(self) -> None:
        cfg = {
            "skills": {
                "weather": {"enabled": True},
                "home_assistant": {"enabled": False},
                "music": {"enabled": True},
                "timers": {"enabled": True},
            },
            "home_assistant": {},
        }
        self.reg = SkillRegistry(cfg)
        self.reg.weather.run = MagicMock(return_value="погода ок")  # type: ignore
        self.reg.music.run = MagicMock(return_value="музыка ок")  # type: ignore
        self.reg.timers.run = MagicMock(return_value="таймер ок")  # type: ignore

    def test_weather_rule(self) -> None:
        self.assertEqual(self.reg.try_local_rules("какая сегодня погода"), "погода ок")

    def test_timer_rule(self) -> None:
        self.assertEqual(self.reg.try_local_rules("поставь таймер на 5 минут"), "таймер ок")
        self.reg.timers.run.assert_called()

    def test_next_track(self) -> None:
        self.assertEqual(self.reg.try_local_rules("следующий трек"), "музыка ок")


class GeminiParseTests(unittest.TestCase):
    def test_parse_tool_json(self) -> None:
        raw = '{"tool":"get_weather","arguments":{}}'
        parsed = GeminiClient._parse_tool(raw)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["tool"], "get_weather")

    def test_parse_plain_text(self) -> None:
        self.assertIsNone(GeminiClient._parse_tool("Привет, сейчас ясно."))


class VadTests(unittest.TestCase):
    def test_end_of_speech(self) -> None:
        vad = EnergyVad(threshold=0.05, silence_ms=100, sample_rate=1000)
        speech = np.ones(200, dtype=np.float32) * 0.2
        silence = np.zeros(200, dtype=np.float32)
        self.assertFalse(vad.process(speech))
        self.assertTrue(vad.process(silence))


if __name__ == "__main__":
    unittest.main()

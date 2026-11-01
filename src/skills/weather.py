from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

WMO_RU = {
    0: "ясно",
    1: "преимущественно ясно",
    2: "переменная облачность",
    3: "пасмурно",
    45: "туман",
    48: "изморозь",
    51: "лёгкая морось",
    61: "небольшой дождь",
    63: "дождь",
    65: "сильный дождь",
    71: "небольшой снег",
    73: "снег",
    75: "сильный снег",
    80: "ливень",
    95: "гроза",
}


class WeatherSkill:
    name = "get_weather"

    def __init__(self, cfg: dict[str, Any], proxy: str | None = None) -> None:
        self.lat = cfg.get("latitude", 55.7558)
        self.lon = cfg.get("longitude", 37.6173)
        self.timezone = cfg.get("timezone", "Europe/Moscow")
        self.enabled = cfg.get("enabled", True)
        self.proxy = (proxy or "").strip() or None

    def tool_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": "Текущая погода и краткий прогноз на сегодня",
            "parameters": {
                "type": "object",
                "properties": {
                    "place": {
                        "type": "string",
                        "description": "Опционально: название места (игнорируется, используется дом)",
                    }
                },
            },
        }

    def run(self, **kwargs: Any) -> str:
        if not self.enabled:
            return "Навык погоды выключен."
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": self.lat,
            "longitude": self.lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code",
            "timezone": self.timezone,
            "forecast_days": 1,
        }
        try:
            client_kwargs: dict[str, Any] = {"timeout": 20.0}
            if self.proxy:
                client_kwargs["proxy"] = self.proxy
                logger.info("weather via proxy %s", self.proxy.split("@")[-1])
            with httpx.Client(**client_kwargs) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.exception("weather failed")
            return f"Не удалось получить погоду: {exc}"

        cur = data.get("current", {})
        daily = data.get("daily", {})
        code = int(cur.get("weather_code", 0))
        desc = WMO_RU.get(code, "переменная погода")
        temp = cur.get("temperature_2m")
        humid = cur.get("relative_humidity_2m")
        wind = cur.get("wind_speed_10m")
        tmax = (daily.get("temperature_2m_max") or [None])[0]
        tmin = (daily.get("temperature_2m_min") or [None])[0]
        return (
            f"Сейчас {temp}°, {desc}. Влажность {humid}%, ветер {wind} км/ч. "
            f"Сегодня от {tmin}° до {tmax}°."
        )

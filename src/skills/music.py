from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MusicSkill:
    name = "play_music"

    def __init__(self, cfg: dict[str, Any]) -> None:
        self.enabled = cfg.get("enabled", True)
        self.host = cfg.get("mpd_host", "127.0.0.1")
        self.port = int(cfg.get("mpd_port", 6600))
        self.password = cfg.get("mpd_password")
        self._client = None

    def tool_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": (
                "Управление музыкой через MPD: play, pause, stop, next, previous, "
                "status, play_playlist, play_search."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "play",
                            "pause",
                            "stop",
                            "next",
                            "previous",
                            "status",
                            "play_playlist",
                            "play_search",
                        ],
                    },
                    "query": {"type": "string", "description": "Имя плейлиста или поисковый запрос"},
                },
                "required": ["action"],
            },
        }

    def _connect(self):
        from mpd import MPDClient

        client = MPDClient()
        client.timeout = 5
        client.idletimeout = None
        client.connect(self.host, self.port)
        if self.password:
            client.password(self.password)
        return client

    def run(self, action: str = "status", query: str | None = None, **_: Any) -> str:
        if not self.enabled:
            return "Музыкальный навык выключен."
        try:
            client = self._connect()
        except Exception as exc:
            logger.exception("MPD connect failed")
            return (
                f"MPD недоступен ({exc}). Установи mpd/mpc и укажи host/port в конфиге."
            )

        try:
            action = (action or "status").lower()
            if action == "play":
                client.play()
                return self._now_playing(client) or "Воспроизведение."
            if action == "pause":
                client.pause(1)
                return "Пауза."
            if action == "stop":
                client.stop()
                return "Стоп."
            if action == "next":
                client.next()
                return self._now_playing(client) or "Следующий трек."
            if action == "previous":
                client.previous()
                return self._now_playing(client) or "Предыдущий трек."
            if action == "play_playlist":
                if not query:
                    return "Укажи имя плейлиста."
                client.clear()
                client.load(query)
                client.play()
                return f"Плейлист «{query}»."
            if action == "play_search":
                if not query:
                    return "Укажи что искать."
                results = client.search("any", query)
                if not results:
                    return f"Ничего не нашёл по «{query}»."
                client.clear()
                for item in results[:50]:
                    file_path = item.get("file")
                    if file_path:
                        client.add(file_path)
                client.play()
                return self._now_playing(client) or f"Играю результаты по «{query}»."
            # status
            return self._now_playing(client) or "Сейчас ничего не играет."
        except Exception as exc:
            logger.exception("MPD command failed")
            return f"Ошибка MPD: {exc}"
        finally:
            try:
                client.close()
                client.disconnect()
            except Exception:
                pass

    @staticmethod
    def _now_playing(client) -> str:
        status = client.status() or {}
        state = status.get("state", "stop")
        cur = client.currentsong() or {}
        title = cur.get("title") or cur.get("file") or ""
        artist = cur.get("artist") or ""
        if state == "stop" and not title:
            return "Сейчас ничего не играет."
        label = f"{artist} — {title}".strip(" —") if artist or title else "неизвестный трек"
        return f"Сейчас ({state}): {label}."

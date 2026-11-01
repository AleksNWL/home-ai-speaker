from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class HomeAssistantSkill:
    name = "ha_call"

    def __init__(self, skills_cfg: dict[str, Any], secrets_ha: dict[str, Any]) -> None:
        cfg = skills_cfg or {}
        self.enabled = cfg.get("enabled", True)
        self.timeout = cfg.get("timeout_seconds", 8)
        self.url = (secrets_ha.get("url") or "").rstrip("/")
        self.token = secrets_ha.get("token") or ""

    def tool_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": (
                "Вызвать сервис Home Assistant: свет, розетки, сцены, скрипты. "
                "domain/service/entity_id как в HA (например light / turn_off / light.kitchen)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "light, switch, scene, script, ..."},
                    "service": {"type": "string", "description": "turn_on, turn_off, toggle, ..."},
                    "entity_id": {"type": "string", "description": "entity_id в HA"},
                    "data": {"type": "object", "description": "Доп. поля сервиса"},
                },
                "required": ["domain", "service"],
            },
        }

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def run(
        self,
        domain: str,
        service: str,
        entity_id: str | None = None,
        data: dict[str, Any] | None = None,
        **_: Any,
    ) -> str:
        if not self.enabled:
            return "Home Assistant skill выключен."
        if not self.url or not self.token:
            return "Home Assistant не настроен: укажи url и token в config/secrets.yaml."

        payload: dict[str, Any] = dict(data or {})
        if entity_id:
            payload["entity_id"] = entity_id

        endpoint = f"{self.url}/api/services/{domain}/{service}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(endpoint, headers=self._headers(), json=payload)
                if resp.status_code >= 400:
                    return f"HA ошибка {resp.status_code}: {resp.text[:200]}"
        except Exception as exc:
            logger.exception("HA call failed")
            return f"Не удалось связаться с Home Assistant: {exc}"

        target = entity_id or domain
        return f"Готово: {domain}.{service} для {target}."

    def get_states_summary(self, limit: int = 30) -> str:
        if not self.url or not self.token:
            return "HA не настроен."
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(f"{self.url}/api/states", headers=self._headers())
                resp.raise_for_status()
                states = resp.json()
        except Exception as exc:
            return f"Не удалось получить состояния: {exc}"
        lines = []
        for st in states[:limit]:
            eid = st.get("entity_id", "")
            if eid.startswith(("light.", "switch.", "scene.", "climate.")):
                lines.append(f"{eid}={st.get('state')}")
        return "\n".join(lines) or "Нет релевантных сущностей."

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Callable

logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini chat with simple tool-calling via JSON protocol (works across SDK versions)."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.5-flash-lite",
        system_prompt: str = "",
        temperature: float = 0.4,
        max_output_tokens: int = 512,
        proxy: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.proxy = (proxy or "").strip() or None
        self._client = None

    def _ensure(self) -> None:
        if self._client is not None:
            return
        if not self.api_key:
            raise RuntimeError("Gemini API key missing (config/secrets.yaml or GEMINI_API_KEY)")
        from google import genai

        kwargs: dict[str, Any] = {"api_key": self.api_key}
        if self.proxy:
            # Ensure child HTTP stacks also see the proxy
            os.environ.setdefault("HTTPS_PROXY", self.proxy)
            os.environ.setdefault("HTTP_PROXY", self.proxy)
            os.environ.setdefault("https_proxy", self.proxy)
            os.environ.setdefault("http_proxy", self.proxy)
            logger.info("Gemini via proxy %s", self._redact_proxy(self.proxy))
            try:
                from google.genai import types

                kwargs["http_options"] = types.HttpOptions(
                    client_args={"proxy": self.proxy},
                )
            except Exception:
                # Older SDK: env vars above are enough for httpx
                pass

        self._client = genai.Client(**kwargs)

    @staticmethod
    def _redact_proxy(url: str) -> str:
        # hide credentials in logs: http://user:pass@host:port -> http://***@host:port
        return re.sub(r"(://[^:/@]+:)[^@]+(@)", r"\1***\2", url)

    def reply(
        self,
        user_text: str,
        tools: list[dict[str, Any]],
        dispatch: Callable[[str, dict[str, Any]], str],
    ) -> str:
        self._ensure()
        assert self._client is not None

        tools_blob = json.dumps(tools, ensure_ascii=False, indent=2)
        system = (
            f"{self.system_prompt.strip()}\n\n"
            "Доступные инструменты (JSON Schema):\n"
            f"{tools_blob}\n\n"
            "Если нужен инструмент, ответь ТОЛЬКО JSON вида:\n"
            '{"tool":"name","arguments":{...}}\n'
            "Иначе ответь обычным текстом для озвучки."
        )

        prompt = f"{system}\n\nПользователь: {user_text}"
        text = self._generate(prompt)
        tool_call = self._parse_tool(text)
        if not tool_call:
            return text.strip()

        name = tool_call.get("tool") or tool_call.get("name")
        args = tool_call.get("arguments") or tool_call.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        result = dispatch(str(name), args)
        followup = (
            f"{system}\n\nПользователь: {user_text}\n"
            f"Результат инструмента {name}: {result}\n"
            "Сформулируй короткий ответ пользователю на русском, без JSON."
        )
        return self._generate(followup).strip() or result

    def _generate(self, prompt: str) -> str:
        assert self._client is not None
        from google.genai import types

        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_output_tokens,
            ),
        )
        text = getattr(response, "text", None) or ""
        if not text and getattr(response, "candidates", None):
            try:
                parts = response.candidates[0].content.parts
                text = "".join(getattr(p, "text", "") or "" for p in parts)
            except Exception:
                text = ""
        logger.info("Gemini raw: %s", (text or "")[:200])
        return text or ""

    @staticmethod
    def _parse_tool(text: str) -> dict[str, Any] | None:
        raw = (text or "").strip()
        if not raw:
            return None
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if fence:
            raw = fence.group(1)
        elif raw.startswith("{") and raw.endswith("}"):
            pass
        else:
            m = re.search(r"\{[^{}]*\"tool\"[^{}]*\}", raw, re.DOTALL)
            if not m:
                return None
            raw = m.group(0)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if isinstance(data, dict) and (data.get("tool") or data.get("name")):
            return data
        return None

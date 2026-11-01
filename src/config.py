from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "default.yaml"
SECRETS_CONFIG = ROOT / "config" / "secrets.yaml"


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(
    config_path: Path | None = None,
    secrets_path: Path | None = None,
) -> dict[str, Any]:
    path = config_path or Path(os.environ.get("HAS_CONFIG", DEFAULT_CONFIG))
    with path.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}

    secrets = secrets_path or Path(os.environ.get("HAS_SECRETS", SECRETS_CONFIG))
    if secrets.exists():
        with secrets.open(encoding="utf-8") as fh:
            secret_data = yaml.safe_load(fh) or {}
        cfg = _deep_merge(cfg, secret_data)

    # Env overrides for CI / quick tests
    gemini = cfg.setdefault("gemini", {})
    if os.environ.get("GEMINI_API_KEY"):
        gemini["api_key"] = os.environ["GEMINI_API_KEY"]
    # Proxy for Gemini (region blocks). Prefer GEMINI_PROXY, then HTTPS_PROXY / ALL_PROXY
    proxy = (
        os.environ.get("GEMINI_PROXY")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
        or os.environ.get("ALL_PROXY")
        or os.environ.get("all_proxy")
    )
    if proxy:
        gemini["proxy"] = proxy
    if os.environ.get("HA_URL"):
        cfg.setdefault("home_assistant", {})["url"] = os.environ["HA_URL"]
    if os.environ.get("HA_TOKEN"):
        cfg.setdefault("home_assistant", {})["token"] = os.environ["HA_TOKEN"]


    for key in ("logs", "cache"):
        rel = cfg.get("paths", {}).get(key)
        if rel:
            p = ROOT / rel
            p.mkdir(parents=True, exist_ok=True)

    return cfg


def resolve_path(path_str: str | None) -> Path | None:
    if not path_str:
        return None
    p = Path(path_str)
    if not p.is_absolute():
        p = ROOT / p
    return p

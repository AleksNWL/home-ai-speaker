from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from src.status import StatusBus

logger = logging.getLogger(__name__)
DISPLAY_DIR = Path(__file__).resolve().parents[1] / "display"


def start_display_server(cfg: dict[str, Any], status: StatusBus) -> None:
    status_cfg = cfg.get("status", {})
    port = int(status_cfg.get("http_port", 8787))
    bind = status_cfg.get("bind", "0.0.0.0")

    def _run() -> None:
        try:
            import asyncio

            from aiohttp import web
        except ImportError:
            logger.warning("aiohttp not installed — display server disabled")
            return

        async def api_status(_request: web.Request) -> web.Response:
            return web.json_response(status.get().to_dict())

        async def index(_request: web.Request) -> web.FileResponse:
            return web.FileResponse(DISPLAY_DIR / "index.html")

        async def _amain() -> None:
            app = web.Application()
            app.router.add_get("/api/status", api_status)
            app.router.add_get("/", index)
            static = DISPLAY_DIR / "static"
            if static.exists():
                app.router.add_static("/static/", static)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, bind, port)
            await site.start()
            logger.info("Display UI on http://%s:%s/", bind, port)
            while True:
                await asyncio.sleep(3600)

        asyncio.run(_amain())

    thread = threading.Thread(target=_run, name="display-server", daemon=True)
    thread.start()

from __future__ import annotations

import argparse
import logging
import signal
import sys
from pathlib import Path

# Allow `python -m src.orchestrator` from repo root
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.display_server import start_display_server
from src.orchestrator.app import SpeakerApp
from src.status import StatusBus


def main() -> int:
    parser = argparse.ArgumentParser(description="home-ai-speaker orchestrator")
    parser.add_argument("--config", default=None)
    parser.add_argument("--secrets", default=None)
    parser.add_argument("--text", default=None, help="Process one text command (no mic)")
    parser.add_argument("--no-display", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    cfg_path = Path(args.config) if args.config else None
    secrets_path = Path(args.secrets) if args.secrets else None
    cfg = load_config(cfg_path, secrets_path)
    status = StatusBus()
    app = SpeakerApp(cfg, status=status)

    if not args.no_display:
        start_display_server(cfg, status)

    if args.text:
        # Offline path for testing skills/LLM without mic wake
        local = app.skills.try_local_rules(args.text)
        if local is not None:
            reply = local
        else:
            try:
                reply = app.llm.reply(
                    args.text,
                    tools=app.skills.tool_schemas(),
                    dispatch=app.skills.dispatch,
                )
            except Exception as exc:
                logging.exception("LLM failed")
                reply = f"Ошибка ИИ: {exc}"
        print(reply)
        try:
            app.speak(reply)
        except Exception:
            logging.exception("TTS/playback failed")
        return 0

    def _shutdown(*_args) -> None:
        logging.info("Shutting down...")
        app.stop()
        # input() in main thread may ignore SIGINT until Enter — force exit
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Must run on main thread: Enter-key wake uses input()/stdin
    print("Колонка запущена. SSH SOCKS (ssh -D 1080) должен быть активен.", flush=True)
    try:
        app.run()
    except (KeyboardInterrupt, SystemExit):
        app.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

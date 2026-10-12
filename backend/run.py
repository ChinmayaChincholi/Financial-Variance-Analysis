"""
Start Variance Studio on this computer.

    python run.py

Runs the backend and the built frontend together on 127.0.0.1 and opens the
default browser. No internet connection is needed or used.
"""

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

if getattr(sys, "frozen", False):  # running as a packaged app
    os.environ.setdefault(
        "VARIANCE_STUDIO_FRONTEND_DIR",
        str(Path(sys._MEIPASS) / "frontend_dist"),
    )

import uvicorn  # noqa: E402

from api.app import _frontend_dist_dir, app  # noqa: E402

HOST = "127.0.0.1"
PORT = int(os.environ.get("VARIANCE_STUDIO_PORT", "8000"))


def _open_browser_when_ready() -> None:
    for _ in range(100):
        try:
            with socket.create_connection((HOST, PORT), timeout=0.3):
                break
        except OSError:
            time.sleep(0.1)
    else:
        return
    webbrowser.open(f"http://{HOST}:{PORT}/")


def main() -> None:
    if _frontend_dist_dir() is None:
        print(
            "The frontend has not been built yet.\n"
            "  cd frontend && npm install && npm run build\n"
            "The API will still start, but there is no user interface to open."
        )
    else:
        threading.Thread(target=_open_browser_when_ready, daemon=True).start()
        print(f"Variance Studio is running at http://{HOST}:{PORT}/  (Ctrl+C to quit)")

    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Entry point: virtual input device + LAN web server + tray/notifications."""

import logging
import os
import socket
import sys
import threading
import time

import uvicorn

# Allow running both as `python server/main.py` and `python -m server.main`.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tray as traymod  # noqa: E402
from i18n import tr  # noqa: E402
from input_device import InputController  # noqa: E402
from web import create_app  # noqa: E402

log = logging.getLogger("lan-mouse-keyboard")


def get_lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def wait_until_started(server, server_thread, timeout: float = 5.0) -> bool:
    """Return True if the uvicorn server binds successfully within *timeout* seconds."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if server.started:
            return True
        if not server_thread.is_alive():
            return False
        time.sleep(0.1)
    return server.started


def make_callbacks(tray, state: dict, lock: threading.Lock, notify_fn):
    """Build on_connect / on_disconnect closures for the WebSocket handler."""

    def on_connect(client_ip: str):
        with lock:
            state["count"] += 1
            count = state["count"]
        log.info("connected: %s (%d active)", client_ip, count)
        notify_fn(tr("New device connected"), tr("{ip} is controlling your PC", ip=client_ip))
        tray.set_connected(count)

    def on_disconnect(client_ip: str):
        with lock:
            state["count"] = max(0, state["count"] - 1)
            count = state["count"]
        log.info("disconnected: %s (%d active)", client_ip, count)
        tray.set_connected(count)

    return on_connect, on_disconnect


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    host = os.environ.get("LMK_HOST", "0.0.0.0")
    port = int(os.environ.get("LMK_PORT", "8765"))
    lan_ip = get_lan_ip()

    try:
        controller = InputController()
    except PermissionError:
        log.error(
            "No permission on /dev/uinput. Run ./install.sh and log in again "
            "(you must be in the 'input' group)."
        )
        sys.exit(1)

    tray = traymod.Tray(lan_ip, port)

    lock = threading.Lock()
    state = {"count": 0}
    on_connect, on_disconnect = make_callbacks(tray, state, lock, traymod.notify)

    app = create_app(controller, on_connect, on_disconnect)
    config = uvicorn.Config(app, host=host, port=port, log_level="warning", access_log=False)
    server = uvicorn.Server(config)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    if not wait_until_started(server, server_thread):
        log.error("Server did not start (port %d in use?). Exiting.", port)
        controller.close()
        sys.exit(1)

    url = f"http://{lan_ip}:{port}"
    log.info("Server up at %s  (open this address on the phone)", url)
    # no "server up" notification: only errors show (the icon/QR already show the address)

    try:
        tray.run()  # blocks until quit
    finally:
        log.info("Shutting down…")
        server.should_exit = True
        controller.close()


if __name__ == "__main__":
    main()

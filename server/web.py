"""FastAPI app: serves the mobile UI and accepts input commands over a
WebSocket. Hardened to only accept connections from the local network."""

import asyncio
import ipaddress
import json
import logging
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

log = logging.getLogger(__name__)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def is_local(host: str) -> bool:
    """True only for private/loopback/link-local addresses."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_private or ip.is_loopback or ip.is_link_local


def _dispatch(controller, msg: dict):
    t = msg.get("t")
    if t == "m":
        controller.move(msg.get("dx", 0), msg.get("dy", 0))
    elif t == "s":
        controller.scroll(msg.get("dx", 0), msg.get("dy", 0))
    elif t == "c":
        controller.click(msg.get("b", "left"))
    elif t == "d":
        controller.button(msg.get("b", "left"), True)
    elif t == "u":
        controller.button(msg.get("b", "left"), False)
    elif t == "k":
        controller.type_text(msg.get("text", ""))
    elif t == "key":
        controller.key(msg.get("code", ""))
    elif t == "combo":
        controller.combo(msg.get("mods", []), msg.get("key", ""))


def create_app(controller, on_connect=None, on_disconnect=None) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def restrict_to_lan(request: Request, call_next):
        client = request.client.host if request.client else ""
        if not is_local(client):
            log.warning("rejected non-local HTTP from %s", client)
            return JSONResponse({"error": "forbidden"}, status_code=403)
        return await call_next(request)

    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        host = websocket.client.host if websocket.client else ""
        if not is_local(host):
            log.warning("rejected non-local WS from %s", host)
            await websocket.close(code=1008)
            return
        await websocket.accept()
        if on_connect:
            on_connect(host)
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except (ValueError, TypeError):
                    continue
                # uinput writes are blocking; keep the event loop responsive.
                await asyncio.to_thread(_dispatch, controller, msg)
        except WebSocketDisconnect:
            pass
        except Exception as ex:  # noqa: BLE001
            log.debug("ws error from %s: %s", host, ex)
        finally:
            if on_disconnect:
                on_disconnect(host)

    # Mounted last so /ws takes precedence. html=True serves index.html at /.
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="static")
    return app

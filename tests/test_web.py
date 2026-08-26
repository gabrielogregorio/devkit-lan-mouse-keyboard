"""Tests for web.py: is_local, _dispatch, HTTP middleware, WebSocket."""
import json
import time

import pytest
from fastapi.testclient import TestClient

from web import create_app, is_local, _dispatch


# ── 3.1  is_local ─────────────────────────────────────────────────────────────

class TestIsLocal:
    @pytest.mark.parametrize("addr", [
        "192.168.0.1",
        "10.0.0.1",
        "172.16.0.1",
        "172.31.255.255",
        "127.0.0.1",
        "169.254.1.1",
        "::1",
        "::ffff:192.168.0.5",  # IPv4-mapped private
    ])
    def test_local_addresses(self, addr):
        assert is_local(addr) is True

    @pytest.mark.parametrize("addr", [
        "8.8.8.8",
        "1.1.1.1",
        "172.32.0.1",
        "2001:4860:4860::8888",
    ])
    def test_nonlocal_addresses(self, addr):
        assert is_local(addr) is False

    @pytest.mark.parametrize("bad", ["notanip", "", "256.256.256.256"])
    def test_invalid_returns_false(self, bad):
        assert is_local(bad) is False


# ── 3.2  _dispatch ────────────────────────────────────────────────────────────

class TestDispatch:
    def test_move(self, fake_ctrl):
        _dispatch(fake_ctrl, {"t": "m", "dx": 3, "dy": 4})
        assert ("move", 3, 4) in fake_ctrl.calls

    def test_move_missing_defaults_to_zero(self, fake_ctrl):
        _dispatch(fake_ctrl, {"t": "m"})
        assert ("move", 0, 0) in fake_ctrl.calls

    def test_scroll(self, fake_ctrl):
        _dispatch(fake_ctrl, {"t": "s", "dx": 0, "dy": -2})
        assert ("scroll", 0, -2) in fake_ctrl.calls

    def test_click_default_left(self, fake_ctrl):
        _dispatch(fake_ctrl, {"t": "c"})
        assert ("click", "left") in fake_ctrl.calls

    def test_click_explicit_button(self, fake_ctrl):
        _dispatch(fake_ctrl, {"t": "c", "b": "middle"})
        assert ("click", "middle") in fake_ctrl.calls

    def test_button_down(self, fake_ctrl):
        _dispatch(fake_ctrl, {"t": "d", "b": "left"})
        assert ("button", "left", True) in fake_ctrl.calls

    def test_button_up(self, fake_ctrl):
        _dispatch(fake_ctrl, {"t": "u", "b": "left"})
        assert ("button", "left", False) in fake_ctrl.calls

    def test_type_text(self, fake_ctrl):
        _dispatch(fake_ctrl, {"t": "k", "text": "oi"})
        assert ("type_text", "oi") in fake_ctrl.calls

    def test_type_text_missing_defaults_empty(self, fake_ctrl):
        _dispatch(fake_ctrl, {"t": "k"})
        assert ("type_text", "") in fake_ctrl.calls

    def test_key(self, fake_ctrl):
        _dispatch(fake_ctrl, {"t": "key", "code": "enter"})
        assert ("key", "enter") in fake_ctrl.calls

    def test_combo(self, fake_ctrl):
        _dispatch(fake_ctrl, {"t": "combo", "mods": ["ctrl"], "key": "c"})
        assert ("combo", ["ctrl"], "c") in fake_ctrl.calls

    def test_combo_missing_mods_defaults_empty(self, fake_ctrl):
        _dispatch(fake_ctrl, {"t": "combo", "key": "c"})
        assert ("combo", [], "c") in fake_ctrl.calls

    def test_unknown_type_noop(self, fake_ctrl):
        _dispatch(fake_ctrl, {"t": "xpto"})
        assert fake_ctrl.calls == []

    def test_missing_t_noop(self, fake_ctrl):
        _dispatch(fake_ctrl, {})
        assert fake_ctrl.calls == []


# ── 3.3  HTTP middleware ───────────────────────────────────────────────────────

class TestHTTPMiddleware:
    def _app(self, fake_ctrl):
        return create_app(fake_ctrl)

    def test_nonlocal_gets_403(self, monkeypatch, fake_ctrl):
        monkeypatch.setattr("web.is_local", lambda h: False)
        client = TestClient(self._app(fake_ctrl), raise_server_exceptions=True)
        resp = client.get("/")
        assert resp.status_code == 403

    def test_local_gets_200_with_html(self, monkeypatch, fake_ctrl):
        monkeypatch.setattr("web.is_local", lambda h: True)
        client = TestClient(self._app(fake_ctrl))
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Touchpad" in resp.text or "touchpad" in resp.text.lower()

    def test_app_js_served(self, monkeypatch, fake_ctrl):
        monkeypatch.setattr("web.is_local", lambda h: True)
        client = TestClient(self._app(fake_ctrl))
        assert client.get("/app.js").status_code == 200

    def test_style_css_served(self, monkeypatch, fake_ctrl):
        monkeypatch.setattr("web.is_local", lambda h: True)
        client = TestClient(self._app(fake_ctrl))
        assert client.get("/style.css").status_code == 200

    def test_missing_route_404(self, monkeypatch, fake_ctrl):
        monkeypatch.setattr("web.is_local", lambda h: True)
        client = TestClient(self._app(fake_ctrl))
        assert client.get("/does-not-exist.xyz").status_code == 404


# ── 3.4  WebSocket /ws ────────────────────────────────────────────────────────

class TestWebSocket:
    def _client(self, monkeypatch, fake_ctrl, connects=None, disconnects=None):
        monkeypatch.setattr("web.is_local", lambda h: True)
        app = create_app(
            fake_ctrl,
            on_connect=connects.append if connects is not None else None,
            on_disconnect=disconnects.append if disconnects is not None else None,
        )
        return TestClient(app)

    def test_connect_fires_on_connect_and_on_disconnect(self, monkeypatch, fake_ctrl):
        connects, disconnects = [], []
        client = self._client(monkeypatch, fake_ctrl, connects, disconnects)
        with client.websocket_connect("/ws"):
            pass
        assert len(connects) == 1
        assert len(disconnects) == 1

    def test_dispatch_move_over_ws(self, monkeypatch, fake_ctrl):
        client = self._client(monkeypatch, fake_ctrl)
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"t": "m", "dx": 5, "dy": 7})
            time.sleep(0.05)  # asyncio.to_thread finishes quickly
        assert ("move", 5, 7) in fake_ctrl.calls

    def test_invalid_json_ignored_connection_stays(self, monkeypatch, fake_ctrl):
        client = self._client(monkeypatch, fake_ctrl)
        with client.websocket_connect("/ws") as ws:
            ws.send_text("{invalid json{{")
            time.sleep(0.05)
            ws.send_json({"t": "m", "dx": 1, "dy": 0})
            time.sleep(0.05)
        assert ("move", 1, 0) in fake_ctrl.calls

    def test_nonlocal_ws_on_connect_not_called(self, monkeypatch, fake_ctrl):
        monkeypatch.setattr("web.is_local", lambda h: False)
        connects = []
        app = create_app(fake_ctrl, on_connect=connects.append)
        client = TestClient(app, raise_server_exceptions=False)
        try:
            with client.websocket_connect("/ws"):
                pass
        except Exception:
            pass
        assert len(connects) == 0

    def test_optional_callbacks_none_ok(self, monkeypatch, fake_ctrl):
        monkeypatch.setattr("web.is_local", lambda h: True)
        app = create_app(fake_ctrl)  # no callbacks
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"t": "key", "code": "enter"})
            time.sleep(0.05)
        assert ("key", "enter") in fake_ctrl.calls

"""Tests for main.py: get_lan_ip, wait_until_started, make_callbacks, PermissionError."""
import socket
import sys
import threading
from unittest.mock import MagicMock, patch

import pytest

import main as main_mod


# ── 4.4a  get_lan_ip ─────────────────────────────────────────────────────────

class TestGetLanIp:
    def test_returns_ipv4_string(self, monkeypatch):
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ("192.168.1.42", 0)
        monkeypatch.setattr("socket.socket", lambda *a, **k: mock_sock)
        assert main_mod.get_lan_ip() == "192.168.1.42"

    def test_oserror_returns_loopback(self, monkeypatch):
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = OSError("no network")
        monkeypatch.setattr("socket.socket", lambda *a, **k: mock_sock)
        assert main_mod.get_lan_ip() == "127.0.0.1"


# ── 4.4b  wait_until_started ──────────────────────────────────────────────────

class TestWaitUntilStarted:
    def test_returns_true_when_already_started(self):
        server = MagicMock(started=True)
        thread = MagicMock()
        thread.is_alive.return_value = True
        assert main_mod.wait_until_started(server, thread, timeout=1.0) is True

    def test_returns_true_after_start(self):
        server = MagicMock(started=False)
        thread = MagicMock()
        thread.is_alive.return_value = True

        def flip():
            import time; time.sleep(0.05)
            server.started = True

        threading.Thread(target=flip, daemon=True).start()
        assert main_mod.wait_until_started(server, thread, timeout=1.0) is True

    def test_returns_false_when_thread_dies(self):
        server = MagicMock(started=False)
        thread = MagicMock()
        thread.is_alive.return_value = False
        result = main_mod.wait_until_started(server, thread, timeout=0.5)
        assert result is False

    def test_returns_false_on_timeout(self):
        server = MagicMock(started=False)
        thread = MagicMock()
        thread.is_alive.return_value = True
        result = main_mod.wait_until_started(server, thread, timeout=0.15)
        assert result is False


# ── 4.4c  make_callbacks ──────────────────────────────────────────────────────

class TestMakeCallbacks:
    def _make(self, initial=0):
        tray = MagicMock()
        state = {"count": initial}
        lock = threading.Lock()
        notify_fn = MagicMock()
        on_connect, on_disconnect = main_mod.make_callbacks(tray, state, lock, notify_fn)
        return on_connect, on_disconnect, tray, state, notify_fn

    def test_connect_increments_counter(self):
        on_connect, _, _, state, _ = self._make()
        on_connect("1.2.3.4")
        assert state["count"] == 1

    def test_connect_calls_notify(self):
        on_connect, _, _, _, notify_fn = self._make()
        on_connect("1.2.3.4")
        notify_fn.assert_called_once()

    def test_connect_updates_tray(self):
        on_connect, _, tray, _, _ = self._make()
        on_connect("1.2.3.4")
        tray.set_connected.assert_called_with(1)

    def test_two_connects_count_two(self):
        on_connect, _, _, state, _ = self._make()
        on_connect("1.1.1.1")
        on_connect("2.2.2.2")
        assert state["count"] == 2

    def test_disconnect_decrements_counter(self):
        on_connect, on_disconnect, _, state, _ = self._make()
        on_connect("1.1.1.1")
        on_disconnect("1.1.1.1")
        assert state["count"] == 0

    def test_disconnect_never_below_zero(self):
        _, on_disconnect, _, state, _ = self._make(initial=0)
        on_disconnect("ghost")  # count was 0
        assert state["count"] == 0

    def test_double_disconnect_never_negative(self):
        on_connect, on_disconnect, _, state, _ = self._make()
        on_connect("x")
        on_disconnect("x")
        on_disconnect("x")  # second disconnect — must not go below 0
        assert state["count"] == 0


# ── 4.4d  main() PermissionError path ────────────────────────────────────────

class TestMainPermissionError:
    def test_exits_with_1_on_permission_error(self, monkeypatch):
        monkeypatch.setattr(main_mod, "get_lan_ip", lambda: "127.0.0.1")
        monkeypatch.setattr(
            main_mod, "InputController", MagicMock(side_effect=PermissionError)
        )
        with pytest.raises(SystemExit) as exc_info:
            main_mod.main()
        assert exc_info.value.code == 1

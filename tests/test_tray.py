"""Tests for tray.py: notify() and Tray headless path."""
import sys
import threading
import time
from unittest.mock import MagicMock

import pytest

import tray as traymod

# ── 4.1  notify() ─────────────────────────────────────────────────────────────

class TestNotify:
    def test_calls_notify_send(self, monkeypatch):
        mock_popen = MagicMock()
        monkeypatch.setattr(traymod.subprocess, "Popen", mock_popen)
        traymod.notify("Title", "Body")
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert "notify-send" in args
        assert "Title" in args
        assert "Body" in args

    def test_notify_includes_app_name_and_icon(self, monkeypatch):
        mock_popen = MagicMock()
        monkeypatch.setattr(traymod.subprocess, "Popen", mock_popen)
        traymod.notify("T", "B")
        args = mock_popen.call_args[0][0]
        assert "-a" in args
        assert "-i" in args

    def test_file_not_found_does_not_raise(self, monkeypatch):
        monkeypatch.setattr(
            traymod.subprocess, "Popen", MagicMock(side_effect=FileNotFoundError)
        )
        traymod.notify("T", "B")  # must not raise


# ── 4.2  Tray headless ────────────────────────────────────────────────────────

@pytest.fixture
def headless_tray(monkeypatch):
    """Force gi to be absent so Tray runs in headless mode."""
    monkeypatch.setitem(sys.modules, "gi", None)
    # Remove any gi sub-modules that may be cached
    for key in list(sys.modules):
        if key == "gi" or key.startswith("gi."):
            monkeypatch.setitem(sys.modules, key, None)
    t = traymod.Tray("127.0.0.1", 8765)
    assert t._available is False
    return t


class TestTrayHeadless:
    def test_available_false(self, headless_tray):
        assert headless_tray._available is False

    def test_set_connected_noop(self, headless_tray):
        headless_tray.set_connected(3)  # must not raise
        headless_tray.set_connected(0)

    def test_run_blocks_until_stop(self, headless_tray):
        done = threading.Event()
        errors = []

        def runner():
            try:
                headless_tray.run()
                done.set()
            except Exception as ex:
                errors.append(ex)

        t = threading.Thread(target=runner, daemon=True)
        t.start()
        time.sleep(0.05)
        assert not done.is_set(), "run() should still be blocking"
        headless_tray.stop()
        t.join(timeout=2.0)
        assert done.is_set(), "run() should return after stop()"
        assert errors == []

    def test_stop_sets_event(self, headless_tray):
        assert not headless_tray._stop.is_set()
        headless_tray.stop()
        assert headless_tray._stop.is_set()

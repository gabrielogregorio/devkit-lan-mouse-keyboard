import sys
import pytest

sys.path.insert(0, "server")


class FakeUInput:
    """Records uinput calls without touching /dev/uinput."""

    def __init__(self, *a, **k):
        self.device = None
        self.calls = []

    def write(self, etype, code, val):
        self.calls.append(("w", etype, code, val))

    def syn(self):
        self.calls.append(("syn",))

    def close(self):
        self.calls.append(("close",))


@pytest.fixture
def fake_ui():
    return FakeUInput()


@pytest.fixture
def ctrl(fake_ui):
    from input_device import InputController
    return InputController(ui_factory=lambda *a, **k: fake_ui)


class FakeCtrl:
    """Records InputController calls without writing to uinput."""

    def __init__(self):
        self.calls = []

    def move(self, dx, dy):
        self.calls.append(("move", dx, dy))

    def scroll(self, dx, dy):
        self.calls.append(("scroll", dx, dy))

    def click(self, b="left"):
        self.calls.append(("click", b))

    def button(self, b, pressed):
        self.calls.append(("button", b, pressed))

    def type_text(self, text):
        self.calls.append(("type_text", text))

    def key(self, code):
        self.calls.append(("key", code))

    def combo(self, mods, key):
        self.calls.append(("combo", mods, key))


@pytest.fixture
def fake_ctrl():
    return FakeCtrl()

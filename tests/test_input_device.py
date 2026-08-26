"""Tests for InputController, CHAR_MAP, SPECIAL_KEYS, MODIFIERS, BUTTONS."""
import pytest
from evdev import ecodes as e

from input_device import (
    InputController,
    CHAR_MAP,
    SPECIAL_KEYS,
    MODIFIERS,
    BUTTONS,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def writes(calls):
    return [c for c in calls if c[0] == "w"]


def syns(calls):
    return [c for c in calls if c[0] == "syn"]


# ── 2.1  Maps ─────────────────────────────────────────────────────────────────

class TestMaps:
    def test_lowercase_letters_no_shift(self):
        for ch in "abcdefghijklmnopqrstuvwxyz":
            kc, shift = CHAR_MAP[ch]
            assert shift is False
            assert kc == getattr(e, f"KEY_{ch.upper()}")

    def test_uppercase_letters_need_shift(self):
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            kc, shift = CHAR_MAP[ch]
            assert shift is True
            assert kc == getattr(e, f"KEY_{ch.upper()}")

    def test_digits_no_shift(self):
        for d in "0123456789":
            kc, shift = CHAR_MAP[d]
            assert shift is False
            assert kc == getattr(e, f"KEY_{d}")

    def test_shift_digits(self):
        for i, ch in enumerate(")!@#$%^&*("):
            kc, shift = CHAR_MAP[ch]
            assert shift is True
            assert kc == getattr(e, f"KEY_{i}")

    def test_punctuation_pairs_share_keycode(self):
        pairs = {
            "`": "~", "-": "_", "=": "+", "[": "{", "]": "}",
            "\\": "|", ";": ":", "'": '"', ",": "<", ".": ">", "/": "?",
        }
        for base, shifted in pairs.items():
            assert CHAR_MAP[base][1] is False, f"{base!r} should not need shift"
            assert CHAR_MAP[shifted][1] is True, f"{shifted!r} should need shift"
            assert CHAR_MAP[base][0] == CHAR_MAP[shifted][0], "same keycode"

    def test_whitespace_entries(self):
        assert CHAR_MAP[" "] == (e.KEY_SPACE, False)
        assert CHAR_MAP["\t"] == (e.KEY_TAB, False)
        assert CHAR_MAP["\n"] == (e.KEY_ENTER, False)

    def test_special_keys_documented_names(self):
        for name in (
            "backspace", "enter", "tab", "space", "esc", "escape",
            "up", "down", "left", "right",
            "home", "end", "pageup", "pagedown", "delete", "del",
        ):
            assert name in SPECIAL_KEYS, f"{name!r} missing from SPECIAL_KEYS"

    def test_modifiers_documented_names(self):
        for name in ("ctrl", "control", "alt", "altgr", "shift", "super", "meta", "win"):
            assert name in MODIFIERS, f"{name!r} missing from MODIFIERS"

    def test_capabilities_include_ev_rel(self):
        seen = {}

        class Cap:
            def __init__(self, caps, **k):
                seen.update(caps)
                self.device = None
            def write(self, *a): pass
            def syn(self): pass
            def close(self): pass

        InputController(ui_factory=Cap)
        assert e.EV_REL in seen
        for rel in (e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL):
            assert rel in seen[e.EV_REL]

    def test_capabilities_include_ev_key(self):
        seen = {}

        class Cap:
            def __init__(self, caps, **k):
                seen.update(caps)
                self.device = None
            def write(self, *a): pass
            def syn(self): pass
            def close(self): pass

        InputController(ui_factory=Cap)
        assert e.EV_KEY in seen
        keys = seen[e.EV_KEY]
        for expected in (
            e.KEY_LEFTSHIFT, e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE,
            e.KEY_LEFTCTRL, e.KEY_ENTER, e.KEY_BACKSPACE,
        ):
            assert expected in keys


# ── 2.2  Mouse ────────────────────────────────────────────────────────────────

class TestMouse:
    def test_move_xy(self, ctrl, fake_ui):
        ctrl.move(5, -3)
        ws = writes(fake_ui.calls)
        assert ("w", e.EV_REL, e.REL_X, 5) in ws
        assert ("w", e.EV_REL, e.REL_Y, -3) in ws
        assert fake_ui.calls[-1] == ("syn",)

    def test_move_zero_zero_noop(self, ctrl, fake_ui):
        ctrl.move(0, 0)
        assert fake_ui.calls == []

    def test_move_only_x_no_rel_y(self, ctrl, fake_ui):
        ctrl.move(1, 0)
        ws = writes(fake_ui.calls)
        assert ("w", e.EV_REL, e.REL_X, 1) in ws
        assert all(c[2] != e.REL_Y for c in ws)

    def test_move_floats_truncated(self, ctrl, fake_ui):
        ctrl.move(2.9, 2.1)
        ws = writes(fake_ui.calls)
        assert ("w", e.EV_REL, e.REL_X, 2) in ws
        assert ("w", e.EV_REL, e.REL_Y, 2) in ws

    def test_scroll_vertical(self, ctrl, fake_ui):
        ctrl.scroll(0, 1)
        assert ("w", e.EV_REL, e.REL_WHEEL, 1) in writes(fake_ui.calls)
        assert fake_ui.calls[-1] == ("syn",)

    def test_scroll_zero_zero_noop(self, ctrl, fake_ui):
        ctrl.scroll(0, 0)
        assert fake_ui.calls == []

    def test_scroll_horizontal(self, ctrl, fake_ui):
        ctrl.scroll(3, 0)
        assert ("w", e.EV_REL, e.REL_HWHEEL, 3) in writes(fake_ui.calls)

    def test_button_pressed(self, ctrl, fake_ui):
        ctrl.button("left", True)
        assert ("w", e.EV_KEY, e.BTN_LEFT, 1) in writes(fake_ui.calls)

    def test_button_released(self, ctrl, fake_ui):
        ctrl.button("left", False)
        assert ("w", e.EV_KEY, e.BTN_LEFT, 0) in writes(fake_ui.calls)

    def test_button_invalid_noop(self, ctrl, fake_ui):
        ctrl.button("inexistente", True)
        assert fake_ui.calls == []

    def test_click_right_down_before_up(self, ctrl, fake_ui):
        ctrl.click("right")
        ws = writes(fake_ui.calls)
        idx1 = next(i for i, c in enumerate(ws) if c == ("w", e.EV_KEY, e.BTN_RIGHT, 1))
        idx0 = next(i for i, c in enumerate(ws) if c == ("w", e.EV_KEY, e.BTN_RIGHT, 0))
        assert idx1 < idx0

    def test_click_default_is_left(self, ctrl, fake_ui):
        ctrl.click()
        ws = writes(fake_ui.calls)
        assert ("w", e.EV_KEY, e.BTN_LEFT, 1) in ws
        assert ("w", e.EV_KEY, e.BTN_LEFT, 0) in ws


# ── 2.3  Keyboard ─────────────────────────────────────────────────────────────

class TestKeyboard:
    def test_type_lowercase_no_shift(self, ctrl, fake_ui):
        ctrl.type_text("a")
        ws = writes(fake_ui.calls)
        assert ("w", e.EV_KEY, e.KEY_A, 1) in ws
        assert ("w", e.EV_KEY, e.KEY_A, 0) in ws
        assert ("w", e.EV_KEY, e.KEY_LEFTSHIFT, 1) not in ws

    def test_type_uppercase_adds_shift(self, ctrl, fake_ui):
        ctrl.type_text("A")
        ws = writes(fake_ui.calls)
        idx_sh_dn = next(i for i, c in enumerate(ws) if c == ("w", e.EV_KEY, e.KEY_LEFTSHIFT, 1))
        idx_a_dn  = next(i for i, c in enumerate(ws) if c == ("w", e.EV_KEY, e.KEY_A, 1))
        idx_sh_up = next(i for i, c in enumerate(ws) if c == ("w", e.EV_KEY, e.KEY_LEFTSHIFT, 0))
        assert idx_sh_dn < idx_a_dn < idx_sh_up

    def test_type_digit_no_shift(self, ctrl, fake_ui):
        ctrl.type_text("1")
        ws = writes(fake_ui.calls)
        assert ("w", e.EV_KEY, e.KEY_1, 1) in ws
        assert ("w", e.EV_KEY, e.KEY_LEFTSHIFT, 1) not in ws

    def test_type_shift_symbol(self, ctrl, fake_ui):
        ctrl.type_text("!")
        ws = writes(fake_ui.calls)
        assert ("w", e.EV_KEY, e.KEY_LEFTSHIFT, 1) in ws
        assert ("w", e.EV_KEY, e.KEY_1, 1) in ws

    def test_type_space(self, ctrl, fake_ui):
        ctrl.type_text(" ")
        assert ("w", e.EV_KEY, e.KEY_SPACE, 1) in writes(fake_ui.calls)

    def test_type_unmapped_char_ignored(self, ctrl, fake_ui):
        ctrl.type_text("ç")
        assert fake_ui.calls == []

    def test_type_empty_noop(self, ctrl, fake_ui):
        ctrl.type_text("")
        assert fake_ui.calls == []

    def test_key_enter(self, ctrl, fake_ui):
        ctrl.key("enter")
        ws = writes(fake_ui.calls)
        assert ("w", e.EV_KEY, e.KEY_ENTER, 1) in ws
        assert ("w", e.EV_KEY, e.KEY_ENTER, 0) in ws

    def test_key_case_insensitive(self, ctrl, fake_ui):
        ctrl.key("ESC")
        assert ("w", e.EV_KEY, e.KEY_ESC, 1) in writes(fake_ui.calls)

    def test_key_del_and_delete_same(self, ctrl, fake_ui):
        ctrl.key("del")
        ws1 = writes(fake_ui.calls)
        fake_ui.calls.clear()
        ctrl.key("delete")
        ws2 = writes(fake_ui.calls)
        assert ws1 == ws2
        assert ("w", e.EV_KEY, e.KEY_DELETE, 1) in ws1

    def test_key_unknown_noop(self, ctrl, fake_ui):
        ctrl.key("xpto")
        assert fake_ui.calls == []

    def test_key_none_noop(self, ctrl, fake_ui):
        ctrl.key(None)
        assert fake_ui.calls == []

    def test_key_empty_noop(self, ctrl, fake_ui):
        ctrl.key("")
        assert fake_ui.calls == []


# ── 2.4  Combos ───────────────────────────────────────────────────────────────

class TestCombos:
    def _ws(self, calls):
        return [c for c in calls if c[0] == "w"]

    def test_ctrl_c_order(self, ctrl, fake_ui):
        ctrl.combo(["ctrl"], "c")
        seq = self._ws(fake_ui.calls)
        ctrl_dn = ("w", e.EV_KEY, e.KEY_LEFTCTRL, 1)
        c_dn    = ("w", e.EV_KEY, e.KEY_C, 1)
        c_up    = ("w", e.EV_KEY, e.KEY_C, 0)
        ctrl_up = ("w", e.EV_KEY, e.KEY_LEFTCTRL, 0)
        for ev in (ctrl_dn, c_dn, c_up, ctrl_up):
            assert ev in seq
        assert seq.index(ctrl_dn) < seq.index(c_dn)
        assert seq.index(c_dn) < seq.index(c_up)
        assert seq.index(c_up) < seq.index(ctrl_up)

    def test_ctrl_alt_delete(self, ctrl, fake_ui):
        ctrl.combo(["ctrl", "alt"], "delete")
        seq = self._ws(fake_ui.calls)
        assert ("w", e.EV_KEY, e.KEY_LEFTCTRL, 1) in seq
        assert ("w", e.EV_KEY, e.KEY_LEFTALT, 1) in seq
        assert ("w", e.EV_KEY, e.KEY_DELETE, 1) in seq
        assert ("w", e.EV_KEY, e.KEY_DELETE, 0) in seq
        assert ("w", e.EV_KEY, e.KEY_LEFTCTRL, 0) in seq
        assert ("w", e.EV_KEY, e.KEY_LEFTALT, 0) in seq

    def test_alt_tab(self, ctrl, fake_ui):
        ctrl.combo(["alt"], "tab")
        seq = self._ws(fake_ui.calls)
        assert ("w", e.EV_KEY, e.KEY_LEFTALT, 1) in seq
        assert ("w", e.EV_KEY, e.KEY_TAB, 1) in seq

    def test_empty_mods(self, ctrl, fake_ui):
        ctrl.combo([], "c")
        seq = self._ws(fake_ui.calls)
        assert ("w", e.EV_KEY, e.KEY_C, 1) in seq
        assert ("w", e.EV_KEY, e.KEY_LEFTCTRL, 1) not in seq

    def test_invalid_mod_filtered(self, ctrl, fake_ui):
        ctrl.combo(["xpto", "ctrl"], "c")
        seq = self._ws(fake_ui.calls)
        assert ("w", e.EV_KEY, e.KEY_LEFTCTRL, 1) in seq
        assert ("w", e.EV_KEY, e.KEY_C, 1) in seq

    def test_shift_auto_added_for_shift_char(self, ctrl, fake_ui):
        # "!" needs shift; shift not in mods → should be added automatically
        ctrl.combo(["ctrl"], "!")
        seq = self._ws(fake_ui.calls)
        assert ("w", e.EV_KEY, e.KEY_LEFTSHIFT, 1) in seq
        assert ("w", e.EV_KEY, e.KEY_1, 1) in seq

    def test_shift_not_duplicated_when_in_mods(self, ctrl, fake_ui):
        # "!" needs shift; shift already in mods → pressed only once
        ctrl.combo(["shift"], "!")
        seq = self._ws(fake_ui.calls)
        shift_downs = [c for c in seq if c == ("w", e.EV_KEY, e.KEY_LEFTSHIFT, 1)]
        assert len(shift_downs) == 1

    def test_shift_mod_with_no_shift_char(self, ctrl, fake_ui):
        # "1" doesn't need shift; passing shift mod → shift pressed once
        ctrl.combo(["shift"], "1")
        seq = self._ws(fake_ui.calls)
        shift_downs = [c for c in seq if c == ("w", e.EV_KEY, e.KEY_LEFTSHIFT, 1)]
        assert len(shift_downs) == 1
        assert ("w", e.EV_KEY, e.KEY_1, 1) in seq

    def test_unknown_key_noop(self, ctrl, fake_ui):
        ctrl.combo(["ctrl"], "xpto")
        assert fake_ui.calls == []

    def test_empty_key_noop(self, ctrl, fake_ui):
        ctrl.combo(["ctrl"], "")
        assert fake_ui.calls == []


# ── 2.5  Robustness ───────────────────────────────────────────────────────────

class TestRobustness:
    def test_close_calls_ui_close(self, ctrl, fake_ui):
        ctrl.close()
        assert ("close",) in fake_ui.calls

    def test_close_idempotent(self, ctrl, fake_ui):
        ctrl.close()
        ctrl.close()  # must not raise

    def test_close_swallows_exception(self):
        class BrokenUI:
            def __init__(self, *a, **k): self.device = None
            def write(self, *a): pass
            def syn(self): pass
            def close(self): raise RuntimeError("broken")

        c = InputController(ui_factory=BrokenUI)
        c.close()  # must not raise

    def test_permission_error_propagates(self):
        def bad(*a, **k): raise PermissionError("no uinput")
        with pytest.raises(PermissionError):
            InputController(ui_factory=bad)

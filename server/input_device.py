"""Virtual mouse + keyboard backed by the Linux uinput subsystem.

Injection happens at the kernel level (evdev/uinput), so it works the same on
X11 and Wayland. Requires read/write access to /dev/uinput (see install.sh:
udev rule + membership of the `input` group).
"""

import logging
import threading

from evdev import UInput, ecodes as e

log = logging.getLogger(__name__)

# Mouse buttons exposed to clients.
BUTTONS = {
    "left": e.BTN_LEFT,
    "right": e.BTN_RIGHT,
    "middle": e.BTN_MIDDLE,
}

# Modifier keys for shortcuts (Ctrl+C, Ctrl+Alt+T, Alt+Tab, ...).
MODIFIERS = {
    "ctrl": e.KEY_LEFTCTRL,
    "control": e.KEY_LEFTCTRL,
    "alt": e.KEY_LEFTALT,
    "altgr": e.KEY_RIGHTALT,
    "shift": e.KEY_LEFTSHIFT,
    "super": e.KEY_LEFTMETA,
    "meta": e.KEY_LEFTMETA,
    "win": e.KEY_LEFTMETA,
}

# Named, non-printable keys the phone can send explicitly.
SPECIAL_KEYS = {
    "backspace": e.KEY_BACKSPACE,
    "enter": e.KEY_ENTER,
    "tab": e.KEY_TAB,
    "space": e.KEY_SPACE,
    "esc": e.KEY_ESC,
    "escape": e.KEY_ESC,
    "up": e.KEY_UP,
    "down": e.KEY_DOWN,
    "left": e.KEY_LEFT,
    "right": e.KEY_RIGHT,
    "home": e.KEY_HOME,
    "end": e.KEY_END,
    "pageup": e.KEY_PAGEUP,
    "pagedown": e.KEY_PAGEDOWN,
    "delete": e.KEY_DELETE,
    "del": e.KEY_DELETE,
}


def _build_char_map():
    """Map a printable character -> (keycode, needs_shift) for a US layout."""
    m = {}
    for c in "abcdefghijklmnopqrstuvwxyz":
        kc = getattr(e, f"KEY_{c.upper()}")
        m[c] = (kc, False)
        m[c.upper()] = (kc, True)

    for d in "0123456789":
        m[d] = (getattr(e, f"KEY_{d}"), False)
    for i, c in enumerate(")!@#$%^&*("):  # shift + 0..9
        m[c] = (getattr(e, f"KEY_{i}"), True)

    # base char -> (evdev key name, shifted char)
    pairs = {
        "`": ("KEY_GRAVE", "~"),
        "-": ("KEY_MINUS", "_"),
        "=": ("KEY_EQUAL", "+"),
        "[": ("KEY_LEFTBRACE", "{"),
        "]": ("KEY_RIGHTBRACE", "}"),
        "\\": ("KEY_BACKSLASH", "|"),
        ";": ("KEY_SEMICOLON", ":"),
        "'": ("KEY_APOSTROPHE", '"'),
        ",": ("KEY_COMMA", "<"),
        ".": ("KEY_DOT", ">"),
        "/": ("KEY_SLASH", "?"),
    }
    for base, (keyname, shifted) in pairs.items():
        kc = getattr(e, keyname)
        m[base] = (kc, False)
        m[shifted] = (kc, True)

    m[" "] = (e.KEY_SPACE, False)
    m["\t"] = (e.KEY_TAB, False)
    m["\n"] = (e.KEY_ENTER, False)
    return m


CHAR_MAP = _build_char_map()


class InputController:
    def __init__(self, ui_factory=None):
        if ui_factory is None:
            ui_factory = UInput
        keys = set(SPECIAL_KEYS.values())
        keys |= {kc for kc, _ in CHAR_MAP.values()}
        keys.add(e.KEY_LEFTSHIFT)
        keys |= set(MODIFIERS.values())
        keys |= set(BUTTONS.values())

        capabilities = {
            e.EV_KEY: sorted(keys),
            e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL],
        }
        self.ui = ui_factory(capabilities, name="mousekeyboardwifi")
        # Serialize access: uinput writes from the asyncio worker must not interleave.
        self._lock = threading.Lock()
        dev = getattr(self.ui, "device", None)
        log.info("Virtual input device created (%s)", getattr(dev, "path", "uinput"))

    # -- mouse ---------------------------------------------------------------
    def move(self, dx, dy):
        dx, dy = int(dx), int(dy)
        if not (dx or dy):
            return
        with self._lock:
            if dx:
                self.ui.write(e.EV_REL, e.REL_X, dx)
            if dy:
                self.ui.write(e.EV_REL, e.REL_Y, dy)
            self.ui.syn()

    def scroll(self, dx, dy):
        dx, dy = int(dx), int(dy)
        if not (dx or dy):
            return
        with self._lock:
            if dy:
                self.ui.write(e.EV_REL, e.REL_WHEEL, dy)
            if dx:
                self.ui.write(e.EV_REL, e.REL_HWHEEL, dx)
            self.ui.syn()

    def button(self, name, pressed):
        code = BUTTONS.get(name)
        if code is None:
            return
        with self._lock:
            self.ui.write(e.EV_KEY, code, 1 if pressed else 0)
            self.ui.syn()

    def click(self, name="left"):
        self.button(name, True)
        self.button(name, False)

    # -- keyboard ------------------------------------------------------------
    def _tap(self, code, shift=False):
        with self._lock:
            if shift:
                self.ui.write(e.EV_KEY, e.KEY_LEFTSHIFT, 1)
                self.ui.syn()
            self.ui.write(e.EV_KEY, code, 1)
            self.ui.syn()
            self.ui.write(e.EV_KEY, code, 0)
            self.ui.syn()
            if shift:
                self.ui.write(e.EV_KEY, e.KEY_LEFTSHIFT, 0)
                self.ui.syn()

    def type_text(self, text):
        for ch in text:
            entry = CHAR_MAP.get(ch)
            if entry:
                self._tap(entry[0], entry[1])
            else:
                log.debug("unmapped char: %r", ch)

    def key(self, name):
        code = SPECIAL_KEYS.get((name or "").lower())
        if code is not None:
            self._tap(code)

    def combo(self, mods, key):
        """Press modifiers, tap a key, release — e.g. combo(['ctrl'], 'c')."""
        mod_codes = [MODIFIERS[m] for m in (mods or []) if m in MODIFIERS]

        key = key or ""
        target = None
        if key.lower() in SPECIAL_KEYS:
            target = SPECIAL_KEYS[key.lower()]
        elif len(key) == 1 and key in CHAR_MAP:
            kc, needs_shift = CHAR_MAP[key]
            target = kc
            if needs_shift and e.KEY_LEFTSHIFT not in mod_codes:
                mod_codes.append(e.KEY_LEFTSHIFT)
        if target is None:
            return

        with self._lock:
            for c in mod_codes:
                self.ui.write(e.EV_KEY, c, 1)
            self.ui.syn()
            self.ui.write(e.EV_KEY, target, 1)
            self.ui.syn()
            self.ui.write(e.EV_KEY, target, 0)
            self.ui.syn()
            for c in reversed(mod_codes):
                self.ui.write(e.EV_KEY, c, 0)
            self.ui.syn()

    def close(self):
        try:
            self.ui.close()
        except Exception:
            pass

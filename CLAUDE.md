# CLAUDE.md - LAN Mouse & Keyboard

Rules and context for any agent (or person) that touches this project. Read all of it before
editing. Code, comments, logs and docs are in English; the page is English or Brazilian
Portuguese by the browser language (`web/i18n.js`), and the tray menu and notifications follow
the system language (`server/i18n.py`).

---

## 1. What it is

Control the **mouse and keyboard of an Ubuntu PC from a phone** on the local network, by opening
one address in the phone's browser: **no app, no password, no login**.

- Controls **mouse and keyboard** over the LAN (Wi-Fi or cable, same network).
- **Local network only** (accepts private, loopback and link-local IPs).
- **Ubuntu notification** for every new connected device.
- **Tray icon** showing whether someone is connected (optional, `LMK_NO_TRAY=1` hides it).
- On the phone: **touchpad** (drag moves, tap clicks, 2 fingers scroll) and **keyboard**.
- **systemd user service**, off at login by default (`./install.sh --autostart` turns it on).
- **Receive only**: nothing is ever sent back (no screen capture, files, clipboard).
- No password: type the IP and use it.

Later additions:

- Own **HTML keyboard** (not the phone's), QWERTY + symbol layer + arrows, responsive in
  **portrait and landscape**.
- PC-style keys: **Ctrl, Alt, Super, Esc, Tab, Del** + **real shortcuts** (Ctrl+C, Ctrl+Alt+T,
  Alt+Tab...).
- Keyboard and touchpad **always visible together**.
- **Multitouch**: hold a click button with one finger and move another finger on the touchpad
  (drag/select).

> A "tap-and-drag" gesture (libinput style) existed once and **was reverted** in favor of the
> multitouch "hold the button + move". Do not bring it back without an explicit request.

---

## 2. Architecture

```
┌─────────────┐   HTTP (UI)      ┌──────────────────────────────────────┐
│  Phone      │ ───────────────▶ │  FastAPI (web.py)                    │
│  browser    │   WebSocket /ws  │   - serves web/ (static UI)          │
│  (web/)     │ ◀──────────────▶ │   - receives JSON commands           │
└─────────────┘   JSON commands  │   - guard: local network IPs only    │
                                 └───────────────┬──────────────────────┘
                                                 │ calls
                                                 ▼
                                 ┌──────────────────────────────────────┐
                                 │ InputController (input_device.py)    │
                                 │   evdev UInput → /dev/uinput         │
                                 │   (kernel-level injection)           │
                                 └──────────────────────────────────────┘
            main.py wires it: server (thread) + Tray/notifications (GTK main)
```

- **Input injection** goes through `/dev/uinput` (evdev `UInput`), at kernel level, so it works
  **the same on X11 and Wayland**. No `pynput`/`xdotool`/`ydotool`.
- The **mobile UI is a web page** served by the PC; the phone only needs a browser. Commands
  travel over a **WebSocket** (low latency).
- **One-way for user data**: the server only *receives* commands and injects them.

---

## 3. Files

```
devkit-lan-mouse-keyboard/
├── CLAUDE.md            # this file
├── README.md            # user docs (new PC setup, scripts, CI/CD)
├── VERSION              # release version (bump in the PR)
├── pyproject.toml       # deps + ruff + pytest; uv.lock is the source of truth
├── requirements.txt     # runtime, exported from uv.lock (install.sh uses it)
├── requirements-dev.txt # runtime + tests + ruff, exported from uv.lock (CI uses it)
├── install.sh           # deps + uinput permission + systemd user service
├── uninstall.sh         # removes the service and the udev rule
├── run.sh               # runs in the foreground
├── run-tests.sh         # lint + pytest + node i18n (+ Playwright with RUN_E2E=1)
├── docs/                # README screenshots (metadata stripped)
├── server/
│   ├── main.py          # entry point: wires everything, bind watchdog, callbacks
│   ├── input_device.py  # virtual mouse+keyboard over uinput; key maps
│   ├── web.py           # FastAPI: static files + /ws + local network guard
│   ├── tray.py          # tray icon (AppIndicator) + notify-send
│   └── i18n.py          # tray/notification strings: tr(), PT_BR
├── web/                 # mobile UI (served as static files)
│   ├── index.html
│   ├── style.css
│   ├── i18n.js          # page strings: PT_BR, detectLanguage, translator
│   └── app.js           # ES module: WebSocket, touchpad gestures, on-screen keyboard
└── tests/
    ├── test_*.py        # pytest with a fake UInput and fake controller
    └── frontend/        # i18n.test.mjs (node:test) + Playwright e2e/ with a fake WebSocket
```

---

## 4. Backend (Python)

### `server/input_device.py` - `InputController`
- Creates a `UInput` virtual device named `lan-mouse-keyboard` with `EV_REL` (REL_X, REL_Y,
  REL_WHEEL, REL_HWHEEL) and `EV_KEY` (every key used + mouse buttons + modifiers).
- Methods: `move(dx, dy)`, `scroll(dx, dy)`, `button(name, pressed)` / `click(name)`
  (`left|right|middle`), `type_text(text)` (char by char, **US** layout), `key(name)`,
  `combo(mods, key)` (hold modifiers, tap, release), `close()`.
- A `threading.Lock` serializes uinput writes (dispatch runs in a thread via
  `asyncio.to_thread`).
- `CHAR_MAP`: **US QWERTY** layout, letters (shift for upper case), digits, shift+digit symbols
  and punctuation with shifted pairs. ~97 entries.

### `server/web.py` - FastAPI
- `create_app(controller, on_connect, on_disconnect)`.
- `is_local(host)`: only `ip.is_private | is_loopback | is_link_local` (handles IPv4-mapped
  IPv6). **Every** HTTP request goes through a middleware that returns **403** when not local;
  the WebSocket handler closes with **1008** when not local.
- `GET /` and static files from `web/` (`StaticFiles(html=True)`); `WS /ws` receive loop, each
  JSON message dispatched in `asyncio.to_thread(_dispatch, ...)`.

### `server/tray.py`
- `Tray(ip, port)`: tray icon via `gi` + `AyatanaAppIndicator3` (GTK3). Menu shows the status
  (connected count) and the address. **No Quit item**: the icon stays while the service runs;
  stop the service to turn it off.
- `set_connected(n)` updates the label (via `GLib.idle_add`, thread-safe).
- **Graceful degradation**: without GTK/AppIndicator (or with `LMK_NO_TRAY=1`, used when another
  launcher already shows an icon) it runs *headless*, blocking on an `Event`.
- `notify(title, body)`: `notify-send` (best effort).

### `server/main.py`
- Reads `LMK_HOST` (default `0.0.0.0`) and `LMK_PORT` (default **8765**).
- Creates the `InputController` (clear error and exit 1 without uinput permission).
- Starts uvicorn in a **thread** and waits ~5 s for `server.started`; if it does not bind (port
  in use) it **exits 1** so systemd reports the failure instead of "active" but dead.
- `on_connect`/`on_disconnect` keep a counter (with a lock), notify and update the tray.
- No "server up" notification: only errors show (the icon already shows the address).

---

## 5. WebSocket protocol

Client → server, **JSON**, field `t` = type. Nothing is ever sent back.

| `t`     | Fields                        | Action                                  |
|---------|-------------------------------|-----------------------------------------|
| `m`     | `dx`, `dy`                    | Move the cursor (relative)              |
| `s`     | `dx`, `dy`                    | Scroll (wheel / hwheel)                 |
| `c`     | `b` (`left`/`right`/`middle`) | Click (down+up)                         |
| `d`     | `b`                           | Button **press** (hold)                 |
| `u`     | `b`                           | Button **release**                      |
| `k`     | `text`                        | Type the text (char by char, US)        |
| `key`   | `code`                        | Named special key                       |
| `combo` | `mods` (list), `key`          | Shortcut: hold `mods`, tap `key`, release |

**Special keys (`key.code`)**: `backspace`, `enter`, `tab`, `space`, `esc`/`escape`, `up`,
`down`, `left`, `right`, `home`, `end`, `pageup`, `pagedown`, `delete`/`del`.

**Modifiers (`combo.mods`)**: `ctrl`/`control`, `alt`, `altgr`, `shift`, `super`/`meta`/`win`.
In `combo`, `key` is a character (`"c"`) or a special key (`"tab"`). If the character needs shift
in the layout, shift is added on its own.

---

## 6. Frontend (`web/`)

Dark UI, no external dependencies. `app.js` is an ES module (vanilla JS) that imports `i18n.js`.

### Language
- `detectLanguage(location.search, navigator.languages)`: `?lang=en|pt-BR` wins, else the first
  browser language; `pt*` = pt-BR, anything else English.
- Static text uses `data-i18n` (text) or `data-i18n-html` (markup) with the **English content as
  the key**; dynamic text goes through `t("...")`. Keep the hint markup on one line with `<br>`
  (the browser serializes `<br />` as `<br>` and the key would not match).

### Layout (always visible)
`header` (connection status) → **touchpad** (flex) → **2 click buttons** → **on-screen keyboard**.
Landscape and short screens shrink the keys (media queries on `orientation` and `max-height`).

### Touchpad
- **1 finger drag** → move (`m`), sensitivity `SENS=1.6`, deltas accumulated per
  `requestAnimationFrame`.
- **Quick tap** → left click; **2 fingers** → scroll; **2 finger tap** → right click.
- Uses **`e.targetTouches`** (not `e.touches`): only fingers on the pad itself count, which is
  what makes button+pad multitouch work.

### Click buttons (press and hold)
- `bindHold(id, b)` with **pointer events**: `pointerdown` → `{t:'d'}`,
  `pointerup`/`pointerleave`/`pointercancel` → `{t:'u'}`. Quick tap = normal click.

### On-screen keyboard
- Layers `abc` (QWERTY) and `sym`, switched by `?123`/`ABC`. Function row on both:
  `Esc Tab Ctrl Alt ⊞(Super) ◀ ▲ ▼ ▶ Del`.
- **Shift** one-shot; **Caps Lock** with a double tap on Shift.
- `Ctrl/Alt/Super` stay **armed** until the next key, which sends a `combo`. Several at once work
  (Ctrl+Alt+Del); an armed Shift joins the combo (Ctrl+Shift+T).
- **Repeat on hold** on Backspace and arrows.

### Connection
- `ws://<host>/ws` (or `wss` under https), **auto-reconnect** after 1 s, status dot.

---

## 7. Security and trust model

- **No password by design**: "type the IP and use it".
- Defense = **local network only**: non-local HTTP → 403, non-local WS → close 1008.
- The virtual device only **writes** events; nothing is read or sent back.
- Use it only on a **trusted network**: anyone on it who knows IP:port can control the PC.

---

## 8. Service, autostart and permissions

- systemd **user** unit `~/.config/systemd/user/lan-mouse-keyboard.service`,
  `WantedBy=graphical-session.target` (needs the session D-Bus for tray and notifications),
  `Restart=on-failure`, `Environment=LMK_PORT=8765`. Enabled only with `--autostart`.
- `install.sh` writes the udev rule `99-lan-mouse-keyboard.rules`
  (`KERNEL=="uinput", GROUP="input", MODE="0660"`), loads `uinput` at boot and adds the user to
  the `input` group (**one** relogin).
- **uaccess**: in an active local session `systemd-logind` already grants an ACL
  `user:<you>:rw-` on `/dev/uinput`, so it works before the relogin. The `input` group is what
  survives a reboot. Check with `getfacl /dev/uinput`.
- The venv uses **`--system-site-packages`** so the system `PyGObject` (gi/AppIndicator) is
  visible. The tray needs the apt package `gir1.2-ayatanaappindicator3-0.1`.

---

## 9. Settings

| Variable      | Default   | Description                                   |
|---------------|-----------|-----------------------------------------------|
| `LMK_HOST`    | `0.0.0.0` | Bind interface                                |
| `LMK_PORT`    | `8765`    | HTTP/WebSocket port                           |
| `LMK_NO_TRAY` | unset     | `1` = no own tray icon (headless loop)        |
| `LMK_LANG`    | unset     | `en` or `pt-BR` for tray and notifications    |

> Changing the port? Sync `main.py`, `install.sh` (unit `Environment=`) and the README.

---

## 10. Operation

```bash
./install.sh                 # deps + permissions + service (off at login). Needs sudo.
./install.sh --autostart     # same, and starts with the session
systemctl --user start|stop|restart|status lan-mouse-keyboard
journalctl --user -u lan-mouse-keyboard -f
./run.sh                     # foreground
./uninstall.sh
```

Phone: `http://<PC-IP>:8765` (same network).

> In a shell without the user session exported, prefix `systemctl --user` with
> `XDG_RUNTIME_DIR=/run/user/$(id -u)`.

---

## 11. Development and tests

- `web/` is static: edit and **refresh the phone**, no restart. `server/` needs a restart.
- `./run-tests.sh` = ruff + shellcheck (if installed) + pytest + node i18n; `RUN_E2E=1` adds
  Playwright (after `cd tests/frontend && npm ci`). It must end with `ALL GREEN`.
- Tests **never open `/dev/uinput`** (`FakeUInput` in `conftest.py`) and never start the real
  server: nothing may move the mouse of the PC running them.
- Playwright is **pinned** (`tests/frontend/package-lock.json`, 1.62.0) and runs with
  `locale: en-US`; `?lang=pt-BR` covers the Portuguese page.
- Manual smoke test that does move the real cursor (only when you mean it):
  ```bash
  ./venv/bin/python - <<'PY'
  import sys; sys.path.insert(0, "server")
  from input_device import InputController
  c = InputController()
  c.move(7, 0); c.move(-7, 0); c.scroll(0, 1); c.key("left")
  c.type_text("hi"); c.combo(["ctrl"], "c"); c.close()
  print("ok")
  PY
  ```

## 12. CI/CD and releases

- `.github/workflows/`: `tests.yml` (unit, then e2e with the Playwright report on failure),
  `check-quality.yml` (ruff, shellcheck, `node --check`, exec bit, pinned actions, YAML),
  `codeql-analysis.yml`, `auto-complete-fields.yml` (PR assign/labels/changelog/title, fails if
  `VERSION` is already tagged), `create-tag-and-release.yml` (merged PR → tag `v$VERSION` +
  release with tarball and SHA256SUMS). Shared setup in `.github/actions/setup-environment`.
- Release = bump `VERSION` in the PR and merge. No manual tags.
- **Actions pinned by commit hash** (`uses: owner/repo@<40 hex> # vX.Y.Z`); the lint job fails on
  a tag ref. Runners stay on `ubuntu-24.04`, ruff stays `==` pinned.
- PR text reaches the release through `env:` and a file, never `${{ }}` inside `run:`.
- Deps: edit `pyproject.toml`, `uv lock`, then
  `uv export --frozen --no-dev --no-emit-project --no-hashes -o requirements.txt` and
  `uv export --frozen --all-groups --no-emit-project --no-hashes -o requirements-dev.txt`.

---

## 13. Design decisions and gotchas

- **uinput instead of pynput/xdotool**: the only approach that behaves the same on X11 and
  Wayland. Cost: permission on `/dev/uinput`.
- **`is_private` on Python 3.12**: documentation ranges (`203.0.113.0/24`) count as private.
  Harmless here; in tests use `8.8.8.8`/`1.1.1.1` as "public".
- **`self.ui.device` can be `None`** (evdev does not reopen the node). Use `getattr`.
- **Bind watchdog**: without it a port failure left the process "active" with no server.
- **`targetTouches` vs `touches`**: `touches` is global; a finger on a button would count as a
  2nd finger on the pad and turn into scroll.
- **Pointer events on buttons** give implicit capture on touch, so holding is stable.
- **US layout**: `type_text` assumes US QWERTY; unmapped characters are skipped.

## 14. Known limits / ideas

- The keyboard is the **on-screen HTML** one; the phone's native keyboard/IME is not captured.
- `type_text` is US-only (no accents/IME).
- No authentication (on purpose). An optional PIN could come later without breaking the default.
- Possible: adjustable sensitivity, middle click, media keys, F1-F12, drag lock, 3-finger gestures.

## 15. Conventions

- Every new page string is English, through `data-i18n` or `t("...")`, with its line in
  `web/i18n.js` `PT_BR`; every tray/notification string is English inside `tr()` with its line in
  `server/i18n.py`. The i18n tests fail on a missing line, different `{placeholders}` or an unused
  line.
- Do **not** bring back the reverted tap-and-drag gesture.
- Changing the **protocol** touches three places: `_dispatch` (web.py), the method in
  `input_device.py` and the sender in `app.js`, plus the table in section 5.
- Commits: one line, English.

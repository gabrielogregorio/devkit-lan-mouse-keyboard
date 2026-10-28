import { detectLanguage, translator } from "./i18n.js";

// ===========================================================================
// Language: ?lang= or the browser's first language (pt* = pt-BR)
// ===========================================================================
const language = detectLanguage(location.search, navigator.languages || [navigator.language]);
const t = translator(language);
document.documentElement.lang = language === "pt-BR" ? "pt-BR" : "en";
for (const el of document.querySelectorAll("[data-i18n]")) el.textContent = t(el.textContent.trim());
for (const el of document.querySelectorAll("[data-i18n-html]")) el.innerHTML = t(el.innerHTML.trim());

// ===========================================================================
// WebSocket with auto-reconnect
// ===========================================================================
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");

let ws = null;
let connected = false;

function setStatus(state, text) {
  statusDot.className = "dot" + (state ? " " + state : "");
  statusText.textContent = text;
}

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onopen = () => {
    connected = true;
    setStatus("ok", t("Connected"));
  };
  ws.onclose = () => {
    connected = false;
    setStatus("bad", t("Reconnecting…"));
    setTimeout(connect, 1000);
  };
  ws.onerror = () => ws.close();
}

function send(obj) {
  if (connected && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
}
const typeText = (text) => send({ t: "k", text });
const sendKey = (code) => send({ t: "key", code });

connect();

// ===========================================================================
// Mouse movement — accumulate deltas, flush once per animation frame
// ===========================================================================
const SENS = 1.6;
let accDX = 0,
  accDY = 0,
  rafPending = false;

function queueMove(dx, dy) {
  accDX += dx;
  accDY += dy;
  if (!rafPending) {
    rafPending = true;
    requestAnimationFrame(flushMove);
  }
}
function flushMove() {
  rafPending = false;
  const dx = Math.round(accDX),
    dy = Math.round(accDY);
  accDX -= dx;
  accDY -= dy;
  if (dx || dy) send({ t: "m", dx, dy });
}

// ===========================================================================
// Touchpad gestures
// ===========================================================================
const pad = document.getElementById("touchpad");
const TAP_MS = 250,
  TAP_MOVE = 10,
  SCROLL_DIV = 8;

let mode = null,
  startTime = 0,
  moved = false,
  last = { x: 0, y: 0 },
  scrollAcc = 0,
  twoFinger = false;

// Only fingers that landed on the pad itself (targetTouches), so a finger
// held on a button elsewhere doesn't get counted as a second finger here.
function avg(touches) {
  let x = 0,
    y = 0;
  for (let i = 0; i < touches.length; i++) {
    x += touches[i].clientX;
    y += touches[i].clientY;
  }
  return { x: x / touches.length, y: y / touches.length };
}

pad.addEventListener(
  "touchstart",
  (e) => {
    e.preventDefault();
    pad.classList.add("active");
    startTime = Date.now();
    moved = false;
    scrollAcc = 0;
    if (e.targetTouches.length >= 2) {
      mode = "scroll";
      twoFinger = true;
    } else mode = "move";
    last = avg(e.targetTouches);
  },
  { passive: false }
);

pad.addEventListener(
  "touchmove",
  (e) => {
    e.preventDefault();
    const p = avg(e.targetTouches);
    const dx = p.x - last.x,
      dy = p.y - last.y;
    if (e.targetTouches.length >= 2) {
      mode = "scroll";
      twoFinger = true;
    }
    if (Math.abs(dx) > TAP_MOVE || Math.abs(dy) > TAP_MOVE) moved = true;
    if (mode === "scroll") {
      scrollAcc += dy;
      const ticks = Math.trunc(scrollAcc / SCROLL_DIV);
      if (ticks !== 0) {
        scrollAcc -= ticks * SCROLL_DIV;
        send({ t: "s", dx: 0, dy: -ticks });
      }
    } else {
      // moving here while a click button is held = drag/select
      queueMove(dx * SENS, dy * SENS);
    }
    last = p;
  },
  { passive: false }
);

pad.addEventListener(
  "touchend",
  (e) => {
    e.preventDefault();
    if (e.targetTouches.length === 0) {
      pad.classList.remove("active");
      const quick = Date.now() - startTime < TAP_MS;
      if (quick && !moved) send({ t: "c", b: twoFinger ? "right" : "left" });
      mode = null;
      twoFinger = false;
    } else last = avg(e.targetTouches);
  },
  { passive: false }
);

// ===========================================================================
// Click buttons — press-and-hold so you can hold the button with one finger
// and drag/select by moving another finger on the touchpad (multitouch).
// A quick tap still works as a normal click (button down + up).
// ===========================================================================
function bindHold(id, b) {
  const el = document.getElementById(id);
  const down = (ev) => {
    ev.preventDefault();
    if (el.classList.contains("held")) return;
    el.classList.add("held");
    send({ t: "d", b });
  };
  const up = () => {
    if (!el.classList.contains("held")) return;
    el.classList.remove("held");
    send({ t: "u", b });
  };
  el.addEventListener("pointerdown", down);
  el.addEventListener("pointerup", up);
  el.addEventListener("pointerleave", up);
  el.addEventListener("pointercancel", up);
}
bindHold("btn-left", "left");
bindHold("btn-right", "right");

// ===========================================================================
// On-screen keyboard (always visible) with PC-style modifiers + shortcuts
// ===========================================================================
// Token keys are wrapped in {}. Everything else is a literal character.
const FN_ROW = [
  "{esc}", "{tab}", "{ctrl}", "{alt}", "{super}",
  "{left}", "{up}", "{down}", "{right}", "{del}",
];
const LAYERS = {
  abc: [
    FN_ROW,
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
    ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
    ["a", "s", "d", "f", "g", "h", "j", "k", "l"],
    ["{shift}", "z", "x", "c", "v", "b", "n", "m", "{bksp}"],
    ["{sym}", ",", "{space}", ".", "{enter}"],
  ],
  sym: [
    FN_ROW,
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
    ["@", "#", "$", "_", "&", "-", "+", "(", ")", "/"],
    ["*", '"', "'", ":", ";", "!", "?", "=", "%"],
    ["{shift}", "~", "`", "|", "\\", "[", "]", "{bksp}"],
    ["{abc}", "<", "{space}", ">", "{enter}"],
  ],
};

// label, css classes, and behaviour for each special token.
const SPECIAL = {
  "{esc}": { label: "Esc", cls: "mod fn", key: "esc" },
  "{tab}": { label: "Tab", cls: "mod fn", key: "tab" },
  "{ctrl}": { label: "Ctrl", cls: "mod", mod: "ctrl" },
  "{alt}": { label: "Alt", cls: "mod", mod: "alt" },
  "{super}": { label: "⊞", cls: "mod", mod: "super" },
  "{left}": { label: "◀", cls: "fn", key: "left", repeat: true },
  "{up}": { label: "▲", cls: "fn", key: "up", repeat: true },
  "{down}": { label: "▼", cls: "fn", key: "down", repeat: true },
  "{right}": { label: "▶", cls: "fn", key: "right", repeat: true },
  "{del}": { label: "Del", cls: "mod fn", key: "delete" },
  "{shift}": { label: "⇧", cls: "mod wide", action: "shift" },
  "{bksp}": { label: "⌫", cls: "mod wide", key: "backspace", repeat: true },
  "{sym}": { label: "?123", cls: "mod wide", action: "sym" },
  "{abc}": { label: "ABC", cls: "mod wide", action: "abc" },
  "{enter}": { label: "⏎", cls: "mod wider", key: "enter" },
  "{space}": { label: "", cls: "space", text: " " },
};

const keysEl = document.getElementById("kb-keys");

let layer = "abc";
let shift = false; // one-shot capitalisation
let caps = false; // sticky caps lock
let lastShiftTap = 0;
const mods = { ctrl: false, alt: false, super: false }; // armed modifiers

function activeMods() {
  return ["ctrl", "alt", "super"].filter((m) => mods[m]);
}
function clearMods() {
  mods.ctrl = mods.alt = mods.super = false;
  shift = false; // a one-shot shift is consumed by a combo
  render();
}

function render() {
  keysEl.innerHTML = "";
  for (const row of LAYERS[layer]) {
    const rowEl = document.createElement("div");
    rowEl.className = "kb-row";
    for (const token of row) rowEl.appendChild(makeKey(token));
    keysEl.appendChild(rowEl);
  }
}

function makeKey(token) {
  const el = document.createElement("div");
  el.className = "key";
  const spec = SPECIAL[token];

  if (spec) {
    el.className += " " + spec.cls;
    el.textContent = spec.label;
    el.dataset.token = token;
    if (spec.mod && mods[spec.mod]) el.classList.add("armed");
    if (token === "{shift}") {
      if (caps) {
        el.textContent = "⇪";
        el.classList.add("armed");
      } else if (shift) {
        el.classList.add("armed");
      }
    }
  } else {
    const up = layer === "abc" && (shift || caps);
    el.textContent = up ? token.toUpperCase() : token;
    el.dataset.char = up ? token.toUpperCase() : token;
    el.dataset.base = token; // lowercase base, used for shortcuts
  }
  attachKey(el);
  return el;
}

let repeatTimer = null,
  repeatInterval = null;
function stopRepeat() {
  clearTimeout(repeatTimer);
  clearInterval(repeatInterval);
  repeatTimer = repeatInterval = null;
}

function attachKey(el) {
  el.addEventListener(
    "pointerdown",
    (ev) => {
      ev.preventDefault();
      el.classList.add("held");
      fireKey(el);
      const spec = el.dataset.token && SPECIAL[el.dataset.token];
      if (spec && spec.repeat) {
        repeatTimer = setTimeout(() => {
          repeatInterval = setInterval(() => fireKey(el), 60);
        }, 350);
      }
    },
    { passive: false }
  );
  const release = () => {
    el.classList.remove("held");
    stopRepeat();
  };
  el.addEventListener("pointerup", release);
  el.addEventListener("pointerleave", release);
  el.addEventListener("pointercancel", release);
}

function fireKey(el) {
  const token = el.dataset.token;
  const spec = token ? SPECIAL[token] : null;

  // Modifier toggles (Ctrl / Alt / Super) — stay armed until the next key.
  if (spec && spec.mod) {
    mods[spec.mod] = !mods[spec.mod];
    render();
    return;
  }
  if (spec && spec.action === "shift") {
    const now = Date.now();
    if (now - lastShiftTap < 350) {
      caps = !caps;
      shift = false;
    } else {
      shift = !shift;
      if (shift) caps = false;
    }
    lastShiftTap = now;
    render();
    return;
  }
  if (spec && spec.action === "sym") {
    layer = "sym";
    render();
    return;
  }
  if (spec && spec.action === "abc") {
    layer = "abc";
    render();
    return;
  }

  const am = activeMods();

  // Literal character key
  if (el.dataset.base !== undefined) {
    if (am.length) {
      const combo = am.slice();
      if (shift || caps) combo.push("shift");
      send({ t: "combo", mods: combo, key: el.dataset.base });
      clearMods();
    } else {
      typeText(el.dataset.char);
      if (shift && !caps) {
        shift = false;
        render();
      }
    }
    return;
  }

  // Special key that maps to a key code (enter, tab, arrows, backspace…)
  if (spec && spec.key) {
    if (am.length) {
      send({ t: "combo", mods: am, key: spec.key });
      clearMods();
    } else {
      sendKey(spec.key);
    }
    return;
  }

  // Space
  if (spec && spec.text !== undefined) {
    if (am.length) {
      send({ t: "combo", mods: am, key: "space" });
      clearMods();
    } else {
      typeText(spec.text);
    }
  }
}

render(); // keyboard is shown from the start

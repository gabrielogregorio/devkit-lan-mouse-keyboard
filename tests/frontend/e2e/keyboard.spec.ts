import {
  test, expect,
  getSent, clearSent, waitConnected,
} from "../fixtures/ws-stub";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await waitConnected(page);
});

// helper: tap a key by its visible label text within the keyboard
async function tapKey(page: any, label: string) {
  // Use text content selector within the keyboard area
  const el = page.locator(`#kb-keys .key`, { hasText: new RegExp(`^${escapeRe(label)}$`) }).first();
  await el.dispatchEvent("pointerdown", { bubbles: true, cancelable: true });
  await el.dispatchEvent("pointerup",   { bubbles: true, cancelable: true });
}

// helper: tap a character key by its base (lowercase) character, whatever Shift shows on it
async function tapChar(page: any, char: string) {
  const el = page.locator(`#kb-keys [data-base="${char}"]`).first();
  await el.dispatchEvent("pointerdown", { bubbles: true, cancelable: true });
  await el.dispatchEvent("pointerup",   { bubbles: true, cancelable: true });
}

// helper: press a key that re-renders the keyboard (layer switch, Shift). The app acts on
// pointerdown and rebuilds the keys, so a pointerup would wait for an element that is gone.
async function pressToken(page: any, token: string) {
  await page.locator(`#kb-keys [data-token="${token}"]`).dispatchEvent("pointerdown", { bubbles: true, cancelable: true });
}

function escapeRe(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// ── 5.4.1  Literal character ──────────────────────────────────────────────────
test("tap 'a' sends k message with text a", async ({ page }) => {
  await clearSent(page);
  await tapChar(page, "a");
  const msgs = await getSent(page);
  expect(msgs).toContainEqual({ t: "k", text: "a" });
});

// ── 5.4.2  Shift one-shot ─────────────────────────────────────────────────────
test("shift one-shot: next letter is uppercase, then resets", async ({ page }) => {
  await clearSent(page);
  await pressToken(page, "{shift}");        // shift armed
  await tapChar(page, "a");       // should send "A"
  await tapChar(page, "b");       // should send "b" (shift consumed)

  const msgs = await getSent(page);
  const texts = msgs.filter((m) => m.t === "k").map((m) => m.text);
  expect(texts).toContain("A");
  const idxA = texts.indexOf("A");
  expect(texts[idxA + 1]).toBe("b");
});

// ── 5.4.3  Caps Lock: double tap shift ────────────────────────────────────────
test("double-tap shift enables caps lock, stays uppercase", async ({ page }) => {
  await clearSent(page);
  // Double tap within 350ms
  await pressToken(page, "{shift}");
  await pressToken(page, "{shift}");

  await tapChar(page, "a");
  await tapChar(page, "b");

  const msgs = await getSent(page);
  const texts = msgs.filter((m) => m.t === "k").map((m) => m.text);
  expect(texts).toContain("A");
  expect(texts).toContain("B");
});

// ── 5.4.4  Layer switch: ?123 / ABC ──────────────────────────────────────────
test("tap ?123 switches to sym layer, ABC switches back", async ({ page }) => {
  await clearSent(page);
  // Switch to sym layer
  await pressToken(page, "{sym}");

  // "@" is on sym layer
  const atEl = page.locator(`[data-char="@"]`).first();
  await atEl.dispatchEvent("pointerdown", { bubbles: true, cancelable: true });
  await atEl.dispatchEvent("pointerup",   { bubbles: true, cancelable: true });

  // Switch back to abc layer
  await pressToken(page, "{abc}");
  // "a" should now be visible
  const aEl = page.locator(`[data-char="a"]`).first();
  await aEl.dispatchEvent("pointerdown", { bubbles: true, cancelable: true });
  await aEl.dispatchEvent("pointerup",   { bubbles: true, cancelable: true });

  const msgs = await getSent(page);
  const texts = msgs.filter((m) => m.t === "k").map((m) => m.text);
  expect(texts).toContain("@");
  expect(texts).toContain("a");
});

// ── 5.4.5  Ctrl modifier armed → combo ────────────────────────────────────────
test("armed Ctrl + c sends combo", async ({ page }) => {
  await clearSent(page);
  await tapKey(page, "Ctrl");     // arm ctrl
  await tapChar(page, "c");       // fire combo

  const msgs = await getSent(page);
  const combos = msgs.filter((m) => m.t === "combo");
  expect(combos.length).toBeGreaterThan(0);
  const c = combos[0];
  expect(c.mods).toContain("ctrl");
  expect(c.key).toBe("c");
});

// ── 5.4.6  Ctrl disarmed after combo ─────────────────────────────────────────
test("ctrl disarms after the combo fires", async ({ page }) => {
  await clearSent(page);
  await tapKey(page, "Ctrl");
  await tapChar(page, "c");
  // Ctrl should no longer be armed; next key is plain
  await clearSent(page);
  await tapChar(page, "a");
  const msgs = await getSent(page);
  expect(msgs).toContainEqual({ t: "k", text: "a" });
  expect(msgs.filter((m) => m.t === "combo")).toHaveLength(0);
});

// ── 5.4.7  Multi-modifier: Ctrl + Alt + Del ───────────────────────────────────
test("Ctrl+Alt+Del sends combo with both mods", async ({ page }) => {
  await clearSent(page);
  await tapKey(page, "Ctrl");
  await tapKey(page, "Alt");
  // Del key
  const delEl = page.locator(`#kb-keys .key`).filter({ hasText: /^Del$/ }).first();
  await delEl.dispatchEvent("pointerdown", { bubbles: true, cancelable: true });
  await delEl.dispatchEvent("pointerup",   { bubbles: true, cancelable: true });

  const msgs = await getSent(page);
  const combos = msgs.filter((m) => m.t === "combo");
  expect(combos.length).toBe(1);
  expect(combos[0].mods).toContain("ctrl");
  expect(combos[0].mods).toContain("alt");
  expect(combos[0].key).toBe("delete");
});

// ── 5.4.8  Ctrl+Shift+T ───────────────────────────────────────────────────────
test("Ctrl+Shift+T includes shift in mods", async ({ page }) => {
  await clearSent(page);
  await tapKey(page, "Ctrl");
  await pressToken(page, "{shift}");
  await tapChar(page, "t");

  const msgs = await getSent(page);
  const combos = msgs.filter((m) => m.t === "combo");
  expect(combos.length).toBe(1);
  expect(combos[0].mods).toContain("ctrl");
  expect(combos[0].mods).toContain("shift");
  expect(combos[0].key).toBe("t");
});

// ── 5.4.9  Special keys ───────────────────────────────────────────────────────
test("Esc sends key esc", async ({ page }) => {
  await clearSent(page);
  const escEl = page.locator(`#kb-keys .key`).filter({ hasText: /^Esc$/ }).first();
  await escEl.dispatchEvent("pointerdown", { bubbles: true, cancelable: true });
  await escEl.dispatchEvent("pointerup",   { bubbles: true, cancelable: true });
  expect(await getSent(page)).toContainEqual({ t: "key", code: "esc" });
});

test("Tab sends key tab", async ({ page }) => {
  await clearSent(page);
  const tabEl = page.locator(`#kb-keys .key`).filter({ hasText: /^Tab$/ }).first();
  await tabEl.dispatchEvent("pointerdown", { bubbles: true, cancelable: true });
  await tabEl.dispatchEvent("pointerup",   { bubbles: true, cancelable: true });
  expect(await getSent(page)).toContainEqual({ t: "key", code: "tab" });
});

test("Del sends key delete", async ({ page }) => {
  await clearSent(page);
  const delEl = page.locator(`#kb-keys .key`).filter({ hasText: /^Del$/ }).first();
  await delEl.dispatchEvent("pointerdown", { bubbles: true, cancelable: true });
  await delEl.dispatchEvent("pointerup",   { bubbles: true, cancelable: true });
  expect(await getSent(page)).toContainEqual({ t: "key", code: "delete" });
});

test("right arrow sends key right", async ({ page }) => {
  await clearSent(page);
  const rightEl = page.locator(`#kb-keys .key`).filter({ hasText: /^▶$/ }).first();
  await rightEl.dispatchEvent("pointerdown", { bubbles: true, cancelable: true });
  await rightEl.dispatchEvent("pointerup",   { bubbles: true, cancelable: true });
  expect(await getSent(page)).toContainEqual({ t: "key", code: "right" });
});

// ── 5.4.10  Enter and Space ────────────────────────────────────────────────────
test("Enter sends key enter", async ({ page }) => {
  await clearSent(page);
  const enterEl = page.locator(`#kb-keys .key`).filter({ hasText: /^⏎$/ }).first();
  await enterEl.dispatchEvent("pointerdown", { bubbles: true, cancelable: true });
  await enterEl.dispatchEvent("pointerup",   { bubbles: true, cancelable: true });
  expect(await getSent(page)).toContainEqual({ t: "key", code: "enter" });
});

test("space key sends k with text space", async ({ page }) => {
  await clearSent(page);
  const spaceEl = page.locator(`#kb-keys .space`).first();
  await spaceEl.dispatchEvent("pointerdown", { bubbles: true, cancelable: true });
  await spaceEl.dispatchEvent("pointerup",   { bubbles: true, cancelable: true });
  const msgs = await getSent(page);
  expect(msgs).toContainEqual({ t: "k", text: " " });
});

// ── 5.4.11  Space with armed Ctrl ─────────────────────────────────────────────
test("armed Ctrl + space sends combo with key space", async ({ page }) => {
  await clearSent(page);
  await tapKey(page, "Ctrl");
  const spaceEl = page.locator(`#kb-keys .space`).first();
  await spaceEl.dispatchEvent("pointerdown", { bubbles: true, cancelable: true });
  await spaceEl.dispatchEvent("pointerup",   { bubbles: true, cancelable: true });
  const msgs = await getSent(page);
  const combos = msgs.filter((m) => m.t === "combo");
  expect(combos.length).toBeGreaterThan(0);
  expect(combos[0].mods).toContain("ctrl");
  expect(combos[0].key).toBe("space");
});

// ── 5.4.12  Backspace repeat on hold ─────────────────────────────────────────
test("holding backspace triggers repeat messages", async ({ page }) => {
  await clearSent(page);
  const bkspEl = page.locator(`#kb-keys .key`).filter({ hasText: /^⌫$/ }).first();
  await bkspEl.dispatchEvent("pointerdown", { bubbles: true, cancelable: true });
  // Wait long enough for the repeat timer (350ms initial + some ticks)
  await page.waitForTimeout(600);
  await bkspEl.dispatchEvent("pointerup", { bubbles: true, cancelable: true });

  const msgs = await getSent(page);
  const bksps = msgs.filter((m) => m.t === "key" && m.code === "backspace");
  expect(bksps.length).toBeGreaterThan(1);
});

// ── 5.4.13  Arrow with modifier ───────────────────────────────────────────────
test("armed Ctrl + right arrow sends combo", async ({ page }) => {
  await clearSent(page);
  await tapKey(page, "Ctrl");
  const rightEl = page.locator(`#kb-keys .key`).filter({ hasText: /^▶$/ }).first();
  await rightEl.dispatchEvent("pointerdown", { bubbles: true, cancelable: true });
  await rightEl.dispatchEvent("pointerup",   { bubbles: true, cancelable: true });

  const msgs = await getSent(page);
  const combos = msgs.filter((m) => m.t === "combo");
  expect(combos.length).toBe(1);
  expect(combos[0].mods).toContain("ctrl");
  expect(combos[0].key).toBe("right");
});

import {
  test, expect,
  getSent, clearSent, waitConnected,
  dispatchTouch, flushRaf,
} from "../fixtures/ws-stub";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await waitConnected(page);
});

// ── 5.3.1  Left button: pointerdown → d, pointerup → u ───────────────────────
test("left button pointerdown sends d, pointerup sends u", async ({ page }) => {
  await clearSent(page);
  await page.dispatchEvent("#btn-left", "pointerdown", { bubbles: true, cancelable: true });
  await page.dispatchEvent("#btn-left", "pointerup",   { bubbles: true, cancelable: true });

  const msgs = await getSent(page);
  expect(msgs).toContainEqual({ t: "d", b: "left" });
  expect(msgs).toContainEqual({ t: "u", b: "left" });
  const idxD = msgs.findIndex((m) => m.t === "d" && m.b === "left");
  const idxU = msgs.findIndex((m) => m.t === "u" && m.b === "left");
  expect(idxD).toBeLessThan(idxU);
});

// ── 5.3.2  Right button ───────────────────────────────────────────────────────
test("right button pointerdown sends d, pointerup sends u", async ({ page }) => {
  await clearSent(page);
  await page.dispatchEvent("#btn-right", "pointerdown", { bubbles: true, cancelable: true });
  await page.dispatchEvent("#btn-right", "pointerup",   { bubbles: true, cancelable: true });

  const msgs = await getSent(page);
  expect(msgs).toContainEqual({ t: "d", b: "right" });
  expect(msgs).toContainEqual({ t: "u", b: "right" });
});

// ── 5.3.3  Quick tap = click (down then up immediately) ──────────────────────
test("quick tap on left button is a down+up pair (click)", async ({ page }) => {
  await clearSent(page);
  await page.dispatchEvent("#btn-left", "pointerdown", { bubbles: true, cancelable: true });
  await page.dispatchEvent("#btn-left", "pointerup",   { bubbles: true, cancelable: true });

  const msgs = await getSent(page);
  const ds = msgs.filter((m) => m.t === "d" && m.b === "left");
  const us = msgs.filter((m) => m.t === "u" && m.b === "left");
  expect(ds).toHaveLength(1);
  expect(us).toHaveLength(1);
});

// ── 5.3.4  Hold stable: double pointerdown doesn't double-fire ───────────────
test("double pointerdown does not send second d (held guard)", async ({ page }) => {
  await clearSent(page);
  await page.dispatchEvent("#btn-left", "pointerdown", { bubbles: true, cancelable: true });
  // Second pointerdown while still held — should be ignored
  await page.dispatchEvent("#btn-left", "pointerdown", { bubbles: true, cancelable: true });
  await page.dispatchEvent("#btn-left", "pointerup",   { bubbles: true, cancelable: true });

  const msgs = await getSent(page);
  const ds = msgs.filter((m) => m.t === "d" && m.b === "left");
  expect(ds).toHaveLength(1);
});

// ── 5.3.5  Multitouch: button hold + touchpad move = drag ────────────────────
test("holding button while moving finger on touchpad produces drag sequence", async ({ page }) => {
  await clearSent(page);

  // Hold left button with pointer
  await page.dispatchEvent("#btn-left", "pointerdown", { bubbles: true, cancelable: true });

  // Move a finger on the touchpad (targetTouches only counts pad touches)
  await dispatchTouch(page, "#touchpad", "touchstart", [{ x: 50, y: 50 }]);
  await dispatchTouch(page, "#touchpad", "touchmove",  [{ x: 80, y: 70 }]);
  await flushRaf(page);
  await dispatchTouch(page, "#touchpad", "touchend",   []);

  // Release button
  await page.dispatchEvent("#btn-left", "pointerup", { bubbles: true, cancelable: true });

  const msgs = await getSent(page);
  const idxD = msgs.findIndex((m) => m.t === "d" && m.b === "left");
  const idxU = msgs.findIndex((m) => m.t === "u" && m.b === "left");
  const moves = msgs.filter((m) => m.t === "m");

  expect(idxD).toBeGreaterThanOrEqual(0);
  expect(idxU).toBeGreaterThan(idxD);
  expect(moves.length).toBeGreaterThan(0);

  // All move events should appear between d and u
  for (const m of msgs) {
    if (m.t === "m") {
      const idx = msgs.indexOf(m);
      expect(idx).toBeGreaterThan(idxD);
      expect(idx).toBeLessThan(idxU);
    }
  }
});

// ── 5.3.6  Button hold + two pad fingers = scroll (not drag) ─────────────────
test("holding button + two fingers on pad produces scroll, not extra drag", async ({ page }) => {
  await clearSent(page);

  await page.dispatchEvent("#btn-left", "pointerdown", { bubbles: true, cancelable: true });

  // Two fingers on pad → mode becomes scroll
  await dispatchTouch(page, "#touchpad", "touchstart", [
    { x: 40, y: 50 }, { x: 60, y: 50 },
  ]);
  for (let i = 1; i <= 5; i++) {
    await dispatchTouch(page, "#touchpad", "touchmove", [
      { x: 40, y: 50 + i * 4 }, { x: 60, y: 50 + i * 4 },
    ]);
  }
  await dispatchTouch(page, "#touchpad", "touchend", []);
  await page.dispatchEvent("#btn-left", "pointerup", { bubbles: true, cancelable: true });

  const msgs = await getSent(page);
  const scrolls = msgs.filter((m) => m.t === "s");
  expect(scrolls.length).toBeGreaterThan(0);
});

import {
  test, expect,
  getSent, clearSent, waitConnected,
  dispatchTouch, flushRaf,
} from "../fixtures/ws-stub";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await waitConnected(page);
});

// ── 5.2.1  Move: single-finger drag ──────────────────────────────────────────
test("single-finger drag produces m messages", async ({ page }) => {
  await clearSent(page);
  await dispatchTouch(page, "#touchpad", "touchstart", [{ x: 50, y: 50 }]);
  await dispatchTouch(page, "#touchpad", "touchmove",  [{ x: 80, y: 70 }]);
  await flushRaf(page);
  await dispatchTouch(page, "#touchpad", "touchend",   []);

  const msgs = await getSent(page);
  const moves = msgs.filter((m) => m.t === "m");
  expect(moves.length).toBeGreaterThan(0);
  // delta should be positive (moved right and down), scaled by SENS=1.6
  const totalDx = moves.reduce((s, m) => s + (m.dx ?? 0), 0);
  const totalDy = moves.reduce((s, m) => s + (m.dy ?? 0), 0);
  expect(totalDx).toBeGreaterThan(0);
  expect(totalDy).toBeGreaterThan(0);
});

// ── 5.2.2  Tap = left click ───────────────────────────────────────────────────
test("quick tap (no move) sends left click", async ({ page }) => {
  await clearSent(page);
  // Single finger, no movement between touchstart and touchend
  await dispatchTouch(page, "#touchpad", "touchstart", [{ x: 50, y: 50 }]);
  await dispatchTouch(page, "#touchpad", "touchend",   []);

  const msgs = await getSent(page);
  expect(msgs).toContainEqual({ t: "c", b: "left" });
});

// ── 5.2.3  Move large distance does not generate click ───────────────────────
test("large move does not produce a click", async ({ page }) => {
  await clearSent(page);
  await dispatchTouch(page, "#touchpad", "touchstart", [{ x: 50, y: 50 }]);
  await dispatchTouch(page, "#touchpad", "touchmove",  [{ x: 80, y: 80 }]); // >TAP_MOVE=10
  await flushRaf(page);
  await dispatchTouch(page, "#touchpad", "touchend",   []);

  const msgs = await getSent(page);
  const clicks = msgs.filter((m) => m.t === "c");
  expect(clicks.length).toBe(0);
});

// ── 5.2.4  Two-finger scroll ──────────────────────────────────────────────────
test("two-finger move produces scroll messages", async ({ page }) => {
  await clearSent(page);
  await dispatchTouch(page, "#touchpad", "touchstart", [
    { x: 40, y: 50 }, { x: 60, y: 50 },
  ]);
  // Move both fingers down enough to cross SCROLL_DIV=8 boundary
  for (let i = 0; i < 5; i++) {
    await dispatchTouch(page, "#touchpad", "touchmove", [
      { x: 40, y: 50 + (i + 1) * 4 },
      { x: 60, y: 50 + (i + 1) * 4 },
    ]);
  }
  await dispatchTouch(page, "#touchpad", "touchend", []);

  const msgs = await getSent(page);
  const scrolls = msgs.filter((m) => m.t === "s");
  expect(scrolls.length).toBeGreaterThan(0);
  // Scrolling down should produce negative dy (natural scroll)
  const hasNegDy = scrolls.some((m) => m.dy < 0);
  expect(hasNegDy).toBe(true);
});

// ── 5.2.5  Two-finger tap = right click ──────────────────────────────────────
test("two-finger quick tap sends right click", async ({ page }) => {
  await clearSent(page);
  await dispatchTouch(page, "#touchpad", "touchstart", [
    { x: 40, y: 50 }, { x: 60, y: 50 },
  ]);
  // No touchmove — immediately end
  await dispatchTouch(page, "#touchpad", "touchend", []);

  const msgs = await getSent(page);
  expect(msgs).toContainEqual({ t: "c", b: "right" });
});

// ── 5.2.6  rAF coalescing: multiple touchmove in one frame ───────────────────
test("rapid touchmove events are coalesced per rAF", async ({ page }) => {
  await clearSent(page);
  await dispatchTouch(page, "#touchpad", "touchstart", [{ x: 50, y: 50 }]);

  // Fire 5 touchmove events before flushing rAF
  for (let i = 1; i <= 5; i++) {
    await dispatchTouch(page, "#touchpad", "touchmove", [{ x: 50 + i * 2, y: 50 }]);
  }
  await flushRaf(page);

  await dispatchTouch(page, "#touchpad", "touchend", []);

  const msgs = await getSent(page);
  const moves = msgs.filter((m) => m.t === "m");
  // 5 touchmove events should produce fewer m messages (coalesced by rAF)
  expect(moves.length).toBeLessThan(5);
});

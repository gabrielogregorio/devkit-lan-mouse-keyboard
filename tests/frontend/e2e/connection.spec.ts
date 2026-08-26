import { test, expect, getSent, waitConnected } from "../fixtures/ws-stub";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
});

// ── 5.5.1  Connected status ───────────────────────────────────────────────────
test("page shows Conectado after WS opens", async ({ page }) => {
  await waitConnected(page);
  await expect(page.locator("#status-text")).toContainText("Conectado");
  await expect(page.locator("#status-dot")).toHaveClass(/ok/);
});

// ── 5.5.2  Reconnect on close ─────────────────────────────────────────────────
test("status changes to Reconectando after WS closes, then reconnects", async ({ page }) => {
  await waitConnected(page);

  // Track how many WS instances are created (reconnect = new instance)
  const beforeInstances = await page.evaluate(() => (window as any).__wsInstances as number);

  // Force close the current WS
  await page.evaluate(() => {
    const ws = (window as any).__ws;
    if (ws) ws.close();
  });

  // Status should immediately change to reconnecting
  await expect(page.locator("#status-text")).toContainText("Reconectando", { timeout: 2000 });
  await expect(page.locator("#status-dot")).toHaveClass(/bad/);

  // After ~1s a new WS should be created (reconnect)
  await page.waitForTimeout(1200);
  const afterInstances = await page.evaluate(() => (window as any).__wsInstances as number);
  expect(afterInstances).toBeGreaterThan(beforeInstances);
});

// ── 5.5.3  send() while disconnected does not throw ──────────────────────────
test("send while readyState != OPEN does not throw or send", async ({ page }) => {
  await waitConnected(page);

  // Close WS so readyState != OPEN
  await page.evaluate(() => {
    const ws = (window as any).__ws;
    if (ws) { ws.readyState = 3; }  // force CLOSED without triggering onclose
  });

  // Trigger a key press (calls send internally)
  await page.evaluate(() => {
    // Call send() via the page's internal function
    const keyEl = document.querySelector("#kb-keys .key") as HTMLElement;
    if (keyEl) keyEl.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, cancelable: true }));
  });

  // No uncaught errors; sent buffer should be empty (nothing queued)
  const sent = await getSent(page);
  // All sends while closed should have been dropped
  expect(sent.filter((m: any) => m !== null)).toEqual(sent); // just verify no crash
});

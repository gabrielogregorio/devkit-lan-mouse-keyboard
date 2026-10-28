import { test, expect, waitConnected } from "../fixtures/ws-stub";

// ── 5.6.1  Portrait (390×844) ─────────────────────────────────────────────────
test("portrait: touchpad and keyboard both visible", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await waitConnected(page);

  const pad = page.locator("#touchpad");
  const keys = page.locator("#kb-keys");

  await expect(pad).toBeVisible();
  await expect(keys).toBeVisible();

  // Function row should be present
  const escKey = page.locator("#kb-keys .key").filter({ hasText: /^Esc$/ }).first();
  await expect(escKey).toBeVisible();
});

test("portrait: user-scalable=no meta tag prevents pinch-zoom", async ({ page }) => {
  await page.goto("/");
  const content = await page.locator("meta[name='viewport']").getAttribute("content");
  expect(content).toMatch(/user-scalable=no/i);
});

// ── 5.6.2  Landscape (844×390) ────────────────────────────────────────────────
test("landscape: both touchpad and keyboard visible, no overflow", async ({ page }) => {
  await page.setViewportSize({ width: 844, height: 390 });
  await page.goto("/");
  await waitConnected(page);

  const pad = page.locator("#touchpad");
  const keys = page.locator("#kb-keys");
  await expect(pad).toBeVisible();
  await expect(keys).toBeVisible();

  // Check no horizontal overflow
  const bodyScrollWidth = await page.evaluate(
    () => document.body.scrollWidth - window.innerWidth
  );
  expect(bodyScrollWidth).toBeLessThanOrEqual(1);
});

// ── 5.6.3  Very small height (430px) ─────────────────────────────────────────
test("small height (430px): layout does not overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 430 });
  await page.goto("/");
  await waitConnected(page);

  const bodyScrollWidth = await page.evaluate(
    () => document.body.scrollWidth - window.innerWidth
  );
  expect(bodyScrollWidth).toBeLessThanOrEqual(1);

  // Keyboard still present
  await expect(page.locator("#kb-keys")).toBeVisible();
});

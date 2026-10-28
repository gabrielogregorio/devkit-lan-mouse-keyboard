/**
 * Provides a fake WebSocket that captures sent messages in window.__sent[].
 * Import `test` and `expect` from this module instead of @playwright/test.
 */
import { test as base, type Page } from "@playwright/test";

export { expect } from "@playwright/test";

/** Script injected before any page script loads. */
const WS_STUB = `
(function() {
  window.__sent = [];
  window.__wsInstances = 0;
  class FakeWS {
    constructor(url) {
      this.url = url;
      this.readyState = 0; // CONNECTING
      window.__wsInstances++;
      window.__ws = this; // the latest socket, so a test can close it
      // Simulate async open so the page's onopen handler fires after connect()
      setTimeout(() => {
        this.readyState = 1; // OPEN
        if (this.onopen) this.onopen({ type: 'open' });
      }, 10);
    }
    send(data) {
      if (this.readyState === 1) {
        try { window.__sent.push(JSON.parse(data)); }
        catch (e) { window.__sent.push(data); }
      }
    }
    close() {
      this.readyState = 3; // CLOSED
      if (this.onclose) this.onclose({ code: 1000, reason: '', wasClean: true });
    }
  }
  FakeWS.OPEN = 1;
  FakeWS.CLOSING = 2;
  FakeWS.CLOSED = 3;
  FakeWS.CONNECTING = 0;
  window.WebSocket = FakeWS;
})();
`;

export const test = base.extend<{ page: Page }>({
  page: async ({ page }, use) => {
    await page.addInitScript(WS_STUB);
    await use(page);
  },
});

/** Return all messages sent via the fake WebSocket so far. */
export async function getSent(page: Page): Promise<any[]> {
  return page.evaluate(() => (window as any).__sent as any[]);
}

/** Clear the sent message buffer. */
export async function clearSent(page: Page): Promise<void> {
  await page.evaluate(() => { (window as any).__sent = []; });
}

/** Wait for the fake WS to fire onopen (status = "Connected"). */
export async function waitConnected(page: Page): Promise<void> {
  await page.waitForSelector("#status-dot.ok", { timeout: 2000 });
}

/**
 * Dispatch a synthetic single-finger or multi-finger touch sequence on an element.
 * points: array of {x, y} relative to the element's top-left corner.
 */
export async function dispatchTouch(
  page: Page,
  selector: string,
  type: "touchstart" | "touchmove" | "touchend",
  points: { x: number; y: number }[]
): Promise<void> {
  await page.evaluate(
    ({ selector, type, points }) => {
      const el = document.querySelector(selector) as HTMLElement;
      if (!el) throw new Error(`Element not found: ${selector}`);
      const rect = el.getBoundingClientRect();
      const touches = points.map((p, i) =>
        new Touch({
          identifier: i,
          target: el,
          clientX: rect.left + p.x,
          clientY: rect.top + p.y,
          pageX: rect.left + p.x,
          pageY: rect.top + p.y,
          screenX: rect.left + p.x,
          screenY: rect.top + p.y,
          radiusX: 2,
          radiusY: 2,
          rotationAngle: 0,
          force: 1,
        })
      );
      const evt = new TouchEvent(type, {
        bubbles: true,
        cancelable: true,
        touches: type === "touchend" ? [] : touches,
        targetTouches: type === "touchend" ? [] : touches,
        changedTouches: touches,
      });
      el.dispatchEvent(evt);
    },
    { selector, type, points }
  );
}

/** Flush the rAF-based movement accumulator. */
export async function flushRaf(page: Page): Promise<void> {
  await page.evaluate(
    () => new Promise<void>((r) => requestAnimationFrame(() => r()))
  );
}

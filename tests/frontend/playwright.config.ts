import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:4321",
    hasTouch: true,
    locale: "en-US",
    viewport: { width: 390, height: 844 },
  },
  webServer: {
    command: "python3 -m http.server 4321 --bind 127.0.0.1 --directory ../../web",
    url: "http://127.0.0.1:4321",
    reuseExistingServer: !process.env.CI,
    timeout: 10_000,
  },
  projects: [
    {
      name: "mobile-chrome",
      use: {
        ...devices["Pixel 5"],
        hasTouch: true,
        locale: "en-US",
      },
    },
  ],
});

import { defineConfig, devices } from "@playwright/test";

/**
 * The flows the brief names for step 1.9, against the production image (e2e/compose.yaml).
 * Chromium runs everything; WebKit, Safari's engine, runs the grid's typing and clipboard,
 * which is where Safari differs (the focus catcher in ReleaseGrid.tsx).
 */
export default defineConfig({
  testDir: "tests",
  globalSetup: "./global-setup.ts",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  forbidOnly: !!process.env.CI,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  outputDir: "test-results",
  timeout: 30_000,
  expect: { timeout: 7_500 },
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:8000",
    viewport: { width: 1440, height: 900 },
    locale: "en-GB",
    timezoneId: "Asia/Tokyo",
    acceptDownloads: true,
    trace: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"], viewport: { width: 1440, height: 900 } },
      grep: /@webkit/,
    },
  ],
});

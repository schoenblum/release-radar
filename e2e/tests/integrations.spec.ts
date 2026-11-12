import { generateKeyPairSync } from "node:crypto";

import { expect, test, type Page } from "@playwright/test";

import { ADMIN, Api, cell, daysAgo, openData, reading, tag, value } from "../support";

/** A key file shaped like Google's download, made for this run and never written anywhere. */
function keyFile(): Buffer {
  const { privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  return Buffer.from(
    JSON.stringify({
      type: "service_account",
      project_id: "e2e-project",
      private_key_id: "e2e",
      private_key: privateKey.export({ type: "pkcs8", format: "pem" }).toString(),
      client_email: "e2e-reader@e2e-project.example.org",
    }),
  );
}

async function signInAsAdmin(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN.email);
  await page.getByLabel("Password").fill(ADMIN.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("grid", { name: "Releases" })).toBeVisible();
}

test("Google Analytics: connect, test, fetch now, and see the website views", async ({ page }) => {
  const word = tag();
  const admin = await Api.signIn(ADMIN);
  const counted = await admin.release(`Website views ${word}`, {
    release_date: daysAgo(40),
    website_url: `https://news.example.org/news/e2e-views-321-${word}/`,
  });
  await admin.release(`No data ${word}`, {
    release_date: daysAgo(41),
    website_url: `https://news.example.org/news/e2e-nodata-${word}/`,
  });
  // Still within its 28 days and the 2 days' processing: not fetched yet.
  const recent = await admin.release(`Recent ${word}`, {
    release_date: daysAgo(20),
    website_url: `https://news.example.org/news/e2e-views-5-${word}/`,
  });

  await signInAsAdmin(page);
  await page.goto("/settings/integrations");
  await expect(page.getByRole("heading", { name: "Google Analytics" })).toBeVisible();
  await page.getByLabel(/key \(JSON file\)$/).setInputFiles({
    name: "release-radar-key.json",
    mimeType: "application/json",
    buffer: keyFile(),
  });
  await expect(page.getByText("Key stored for e2e-reader@e2e-project.example.org")).toBeVisible();
  await expect(page.getByText("PRIVATE KEY")).toHaveCount(0);

  const property = page.getByLabel("Property ID", { exact: true });
  await property.fill("123456789");
  await property.press("Enter");
  await expect(page.getByRole("button", { name: "Test connection" })).toBeEnabled();

  await page.getByRole("button", { name: "Test connection" }).click();
  await expect(
    page.getByText(/^Connected\. Google Analytics counted 1,234 page views on news\.example\.org on/),
  ).toBeVisible();

  await page.getByRole("button", { name: "Fetch now" }).click();
  await expect(page.getByText(/^Fetched \d+\. No data for this path: \d+/)).toBeVisible({
    timeout: 20_000,
  });
  // The release with no data stays listed, with its reason; the counted one is gone.
  const waiting = page.getByRole("table");
  await expect(waiting.getByRole("link", { name: `No data ${word}` })).toBeVisible();
  await expect(waiting.getByRole("link", { name: `Website views ${word}` })).toHaveCount(0);
  await expect(page.getByText("Every day, after the nightly backup.", { exact: false })).toBeVisible();

  // The number is on the Data page, read-only there (R7.5.2), and the API agrees.
  const grid = await openData(page, word);
  await expect(value(await cell(grid, `Website views ${word}`, /^Website views/))).toHaveText("321");
  expect(reading(await admin.fetch(counted), "hp_views.d28")).toMatchObject({
    value: 321,
    state: "value",
  });
  expect(reading(await admin.fetch(recent), "hp_views.d28").state).toBe("missing");
  await admin.dispose();
});

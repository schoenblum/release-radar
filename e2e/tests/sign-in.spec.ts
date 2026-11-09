import { expect, test } from "@playwright/test";

import { ADA } from "../support";

test("signing in: a wrong password is explained, the right one opens the Data page", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login/);
  await page.getByLabel("Email").fill(ADA.email);
  await page.getByLabel("Password").fill("not-the-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page).toHaveURL(/\/login/);

  await page.getByLabel("Password").fill(ADA.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("grid", { name: "Releases" })).toBeVisible();
  await expect(page).toHaveURL(/\/data/);

  // The session survives a reload, as it does through a working day (R3.3.5).
  await page.reload();
  await expect(page.getByRole("grid", { name: "Releases" })).toBeVisible();
});

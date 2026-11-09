import { expect, test } from "@playwright/test";

import { ADA, ADA_STATE, Api, BO, cell, copyText, dueRelease, openData, reading, tag } from "../support";

test.use({ storageState: ADA_STATE });

let ada: Api;
let bo: Api;
test.beforeAll(async () => {
  ada = await Api.signIn(ADA);
  bo = await Api.signIn(BO);
});
test.afterAll(async () => {
  await ada.dispose();
  await bo.dispose();
});

const DAY_28 = "EurekAlert views, day 28";

test("a release from a DOI: Crossref fills the paper, then the title is typed", async ({ page }) => {
  const word = tag();
  const grid = await openData(page, word, "mine");
  const box = page.getByLabel(/New release/);
  await box.fill(`https://doi.org/10.5555/e2e.${word}`);
  await box.press("Enter");
  // A new release stays on top, although the search would hide it until it has a title.
  const draft = grid.getByRole("row").filter({ hasText: "No title yet" }).first();
  await expect(draft).toBeVisible();

  await (await cell(grid, "No title yet", "Title")).click();
  await page.keyboard.type(`Frogs sing in chorus ${word}`);
  await page.keyboard.press("Enter");
  await expect(grid.getByRole("row").filter({ hasText: `Frogs sing in chorus ${word}` })).toBeVisible();

  // Its record has the paper from Crossref, and it is a peer-reviewed publication by default.
  await (await cell(grid, word, "Title")).dblclick();
  const record = page.getByRole("dialog");
  await expect(record.getByLabel("Journal")).toHaveValue("Journal of Synthetic Examples");
  await expect(record.getByLabel("Paper title")).toHaveValue(`A synthetic paper about ${word}`);
  await expect(record.getByLabel("Release type")).toHaveText(/Peer-reviewed publication/);
});

test("@webkit editing a cell saves it, and Cmd/Ctrl+Z undoes it", async ({ page }) => {
  const word = tag();
  const release = await dueRelease(ada, `Edited ${word}`);
  const grid = await openData(page, word);
  const views = await cell(grid, word, DAY_28);
  await views.click();
  // Typing replaces, as in a spreadsheet; a thousands separator is fine.
  await page.keyboard.type("1,234");
  await page.keyboard.press("Enter");
  await expect(views).toHaveText("1,234");
  await expect.poll(async () => reading(await ada.fetch(release), "ea_views.d28").value).toBe(1234);

  await views.click();
  await page.keyboard.press("ControlOrMeta+z");
  await expect(views).toHaveText("");
  await expect
    .poll(async () => reading(await ada.fetch(release), "ea_views.d28").state)
    .toBe("missing");
});

test("@webkit pasting a column fills a cell per line, each checked on its own", async ({ page }) => {
  const word = tag();
  // Newest first: the first is on top.
  const first = await dueRelease(ada, `Pasted one ${word}`, 40);
  const second = await dueRelease(ada, `Pasted two ${word}`, 41);
  const third = await dueRelease(ada, `Pasted three ${word}`, 42);
  const grid = await openData(page, word);
  await copyText(page, "120\n2,500\nlots");
  await (await cell(grid, `Pasted one ${word}`, DAY_28)).click();
  await page.keyboard.press("ControlOrMeta+v");

  await expect(page.getByText("2 saved, 1 invalid")).toBeVisible();
  await expect(await cell(grid, `Pasted one ${word}`, DAY_28)).toHaveText("120");
  await expect(await cell(grid, `Pasted two ${word}`, DAY_28)).toHaveText("2,500");
  // The one that is not a number stays on its cell, pink, and is not saved.
  const bad = await cell(grid, `Pasted three ${word}`, DAY_28);
  await expect(bad).toHaveText("lots");
  await expect(bad).toHaveClass(/is-failed/);
  expect(reading(await ada.fetch(first), "ea_views.d28").value).toBe(120);
  expect(reading(await ada.fetch(second), "ea_views.d28").value).toBe(2500);
  expect(reading(await ada.fetch(third), "ea_views.d28").state).toBe("missing");
});

test("N/A: a dash in the grid, or the button in Due now", async ({ page }) => {
  const word = tag();
  const inGrid = await dueRelease(ada, `Dashed ${word}`);
  const inStrip = await dueRelease(ada, `Strip ${word}`, 45);
  const grid = await openData(page, word, "mine");

  const views = await cell(grid, `Dashed ${word}`, DAY_28);
  await views.click();
  await page.keyboard.type("-");
  await page.keyboard.press("Enter");
  await expect(views).toHaveText("N/A");
  await expect
    .poll(async () => reading(await ada.fetch(inGrid), "ea_views.d28").state)
    .toBe("not_applicable");

  const strip = page.getByRole("region", { name: "Due now" });
  const item = strip.getByRole("listitem").filter({ hasText: `Strip ${word}` }).filter({ hasText: DAY_28 });
  await item.getByRole("button", { name: "N/A" }).click();
  await expect(item).toHaveCount(0);
  await expect(await cell(grid, `Strip ${word}`, DAY_28)).toHaveText("N/A");
  expect(reading(await ada.fetch(inStrip), "ea_views.d28").state).toBe("not_applicable");
});

test("a colleague changed the same cell: Release Radar says so, and Keep mine wins", async ({ page }) => {
  const word = tag();
  const release = await ada.release(`Original ${word}`);
  const grid = await openData(page, word);
  const title = await cell(grid, word, "Title");
  await expect(title).toHaveText(`Original ${word}`);

  // Meanwhile Bo renames it, in another browser.
  await bo.set(release, "title", `Bo's title ${word}`);

  await title.click();
  await page.keyboard.type(`Ada's title ${word}`);
  await page.keyboard.press("Enter");
  // Enter moved down a row; back to the cell to read its message.
  await title.click();
  await expect(page.getByRole("alert").filter({ hasText: "Someone else just changed this" })).toContainText(
    `Bo's title ${word}`,
  );
  await page.getByRole("button", { name: "Keep mine" }).click();
  await expect.poll(async () => (await ada.fetch(release)).title).toBe(`Ada's title ${word}`);
  await expect(title).toHaveText(`Ada's title ${word}`);
});

test("sorting from the keyboard: up from the first row, then Enter on a heading", async ({ page }) => {
  const word = tag();
  await ada.release(`Beta ${word}`, { release_date: "2026-05-02" });
  await ada.release(`Alpha ${word}`, { release_date: "2026-05-01" });
  const grid = await openData(page, word);
  const rows = grid.getByRole("row").filter({ hasText: word });
  await expect(rows.first()).toContainText(`Beta ${word}`);

  await (await cell(grid, `Beta ${word}`, "Title")).click();
  await page.keyboard.press("ArrowUp");
  await expect(grid.getByRole("columnheader", { name: "Title" })).toHaveClass(/is-active/);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/sort=title/);
  await expect(rows.first()).toContainText(`Alpha ${word}`);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/sort=-title/);
  await expect(rows.first()).toContainText(`Beta ${word}`);
});

test("the release type: typed in the grid, and found with the filter", async ({ page }) => {
  const word = tag();
  await ada.release(`Paper ${word}`);
  const feature = await ada.release(`Feature ${word}`);
  const grid = await openData(page, word);
  const kind = await cell(grid, `Feature ${word}`, "Release type");
  await expect(kind).toHaveText("Peer-reviewed publication");
  await kind.click();
  await page.keyboard.type("feature");
  await page.keyboard.press("Enter");
  await expect(kind).toHaveText("Feature story");
  await expect.poll(async () => (await ada.fetch(feature)).release_type_id).not.toBe(feature.release_type_id);

  await page.getByRole("combobox", { name: "Release type" }).selectOption({ label: "Feature story" });
  await expect(grid.getByRole("row").filter({ hasText: word })).toHaveCount(1);
  await expect(grid.getByRole("row").filter({ hasText: `Feature ${word}` })).toBeVisible();
  await expect(page).toHaveURL(/type=/);
});

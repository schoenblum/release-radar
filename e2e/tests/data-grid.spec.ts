import { expect, test } from "@playwright/test";

import {
  ADA,
  ADA_STATE,
  Api,
  BO,
  cell,
  copyText,
  dueRelease,
  openData,
  reading,
  tag,
  value,
} from "../support";

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
  await expect(value(views)).toHaveText("1,234");
  await expect.poll(async () => reading(await ada.fetch(release), "ea_views.d28").value).toBe(1234);

  await views.click();
  await page.keyboard.press("ControlOrMeta+z");
  await expect(value(views)).toHaveText("");
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
  await expect(value(await cell(grid, `Pasted one ${word}`, DAY_28))).toHaveText("120");
  await expect(value(await cell(grid, `Pasted two ${word}`, DAY_28))).toHaveText("2,500");
  // The one that is not a number stays on its cell, pink, and is not saved.
  const bad = await cell(grid, `Pasted three ${word}`, DAY_28);
  await expect(value(bad)).toHaveText("lots");
  await expect(bad).toHaveClass(/is-failed/);
  expect(reading(await ada.fetch(first), "ea_views.d28").value).toBe(120);
  expect(reading(await ada.fetch(second), "ea_views.d28").value).toBe(2500);
  expect(reading(await ada.fetch(third), "ea_views.d28").state).toBe("missing");
});

test("dates as people type them, and EurekAlert's US Eastern time kept in Japan time", async ({ page }) => {
  const word = tag();
  const release = await ada.release(`Dated ${word}`);
  const grid = await openData(page, word);
  const date = await cell(grid, word, "Release date");
  // Daniel's examples (2026-11-12): this year's 26 is the year, wherever it stands.
  for (const typed of ["26/11/10", "10/11/26"]) {
    await date.click();
    await page.keyboard.type(typed);
    await page.keyboard.press("Enter");
    await expect(date).toHaveText("2026-11-10");
  }
  // A date and time from EurekAlert: both move to Japan time, the date by a day.
  await date.click();
  await page.keyboard.type("2026-11-10 10:00 ET");
  await page.keyboard.press("Enter");
  await expect(date).toHaveText("2026-11-11");
  await expect
    .poll(async () => {
      const saved = await ada.fetch(release);
      return [saved.release_date, saved.release_time];
    })
    .toEqual(["2026-11-11", "00:00:00"]);
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
  await expect(value(views)).toHaveText("N/A");
  await expect
    .poll(async () => reading(await ada.fetch(inGrid), "ea_views.d28").state)
    .toBe("not_applicable");

  const strip = page.getByRole("region", { name: "Due now" });
  const item = strip.getByRole("listitem").filter({ hasText: `Strip ${word}` }).filter({ hasText: DAY_28 });
  await item.getByRole("button", { name: "N/A" }).click();
  await expect(item).toHaveCount(0);
  await expect(value(await cell(grid, `Strip ${word}`, DAY_28))).toHaveText("N/A");
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

test("@webkit links: pasted as an address or a bare DOI, opened in a new tab from their mark", async ({
  page,
  context,
}) => {
  const word = tag();
  const release = await ada.release(`Linked ${word}`);
  // The EurekAlert page itself is not needed, only that the new tab goes there.
  await context.route("https://www.eurekalert.org/**", (route) =>
    route.fulfill({ contentType: "text/html", body: "<title>EurekAlert stand-in</title>" }),
  );
  const grid = await openData(page, word);

  await copyText(page, `https://doi.org/10.5555/e2e.${word}`);
  await (await cell(grid, word, "DOI")).click();
  await page.keyboard.press("ControlOrMeta+v");
  // Saved bare, and Crossref filled in the paper.
  await expect
    .poll(async () => (await ada.get<{ doi: string }>(`/releases/${release.id}`)).doi)
    .toBe(`10.5555/e2e.${word}`);
  await expect
    .poll(async () => (await ada.get<{ journal: string | null }>(`/releases/${release.id}`)).journal)
    .toBe("Journal of Synthetic Examples");
  const doiLink = (await cell(grid, word, "DOI")).getByRole("link");
  await expect(doiLink).toHaveAttribute("href", `https://doi.org/10.5555/e2e.${word}`);
  await expect(doiLink).toHaveAttribute("target", "_blank");

  const address = "https://www.eurekalert.org/news-releases/1234567";
  await copyText(page, address);
  const eaCell = await cell(grid, word, "EurekAlert link");
  await eaCell.click({ position: { x: 85, y: 18 } });
  await page.keyboard.press("ControlOrMeta+v");
  const eaLink = eaCell.getByRole("link");
  await expect(eaLink).toHaveAttribute("href", address);

  const [tab] = await Promise.all([page.waitForEvent("popup"), eaLink.click()]);
  await tab.waitForURL(address);
  await expect(tab).toHaveTitle("EurekAlert stand-in");
  await tab.close();
  // The grid stayed where it was, with the cell selected.
  await expect(eaCell).toHaveClass(/is-active/);
});

import { readFile } from "node:fs/promises";

import { expect, test, type Locator, type Page } from "@playwright/test";

import { ADA_STATE, ADMIN, Api, daysAgo, reading, tag, type Release } from "../support";

test.use({ storageState: ADA_STATE });

/**
 * The Analysis pages (phase-2 brief §5.6) on synthetic releases. Each test puts its releases in
 * a unit of its own and analyses only that unit, through the address as a bookmark would, so
 * tests never see each other's releases.
 */
interface Made {
  unit: string;
  unitName: string;
  releases: Release[];
}

async function releases(
  word: string,
  specs: { title: string; views: number; age?: number; feature?: boolean }[],
): Promise<Made> {
  const admin = await Api.signIn(ADMIN);
  const unitName = `Unit ${word}`;
  const unit = await admin.send<{ id: string }>("post", "/lists/units", { values: { name_en: unitName } }, 201);
  const types = await admin.get<{ id: string; key: string }[]>("/lists/release_types");
  const feature = types.find((type) => type.key === "feature")?.id;
  const made: Release[] = [];
  for (const [place, spec] of specs.entries()) {
    let release = await admin.release(`${spec.title} ${word}`, {
      release_date: daysAgo(spec.age ?? 40),
      ea_url: `https://www.eurekalert.org/news-releases/${2_000_000 + place + Math.floor(Math.random() * 90_000)}`,
      unit_id: unit.id,
      ...(spec.feature ? { release_type_id: feature } : {}),
    });
    const views = reading(release, "ea_views.d28");
    await admin.send("patch", `/readings/${views.id}`, { version: views.version, value: spec.views });
    release = await admin.fetch(release);
    made.push(release);
  }
  await admin.dispose();
  return { unit: unit.id, unitName, releases: made };
}

function card(page: Page, name: string): Locator {
  return page.getByRole("region", { name });
}

async function median(region: Locator): Promise<string> {
  return (await region.locator(".analysis-median").textContent()) ?? "";
}

test("@webkit the overview: changing what is analysed changes the sentence and the median", async ({ page }) => {
  const word = tag();
  const { unit, unitName } = await releases(word, [
    { title: "One", views: 100 },
    { title: "Two", views: 200 },
    { title: "Three", views: 300 },
    { title: "Four", views: 400 },
    { title: "Five", views: 500 },
    { title: "Feature", views: 900, feature: true },
  ]);
  await page.goto(`/analysis?a_unit=${unit}`);
  await expect(page.getByRole("heading", { level: 1, name: "Overview" })).toBeVisible();
  const sentence = page.locator(".analysis-sentence");
  await expect(sentence).toHaveText(
    new RegExp(`^Analysed releases: 5 \\(Peer-reviewed publication; ${unitName}\\), AY\\d{4}(–AY\\d{4})?\\. Shown: all of them\\.$`),
  );
  const views = card(page, "EurekAlert views, day 28");
  await expect(views).toBeVisible();
  expect(await median(views)).toBe("300");
  // The chart is there, and the CSP kept nothing out: no inline stylesheet to refuse.
  await expect(views.locator("svg.rr-plot").first()).toBeVisible();
  await expect(views.locator("svg style")).toHaveCount(0);

  // Analyse every type: the feature joins the box, and its median moves. What is shown stays
  // where the institution starts it, peer-reviewed publications.
  await page.getByRole("button", { name: "Analysed, Type: Peer-reviewed publication" }).click();
  await page.getByRole("group", { name: "Type" }).getByRole("button", { name: "All", exact: true }).click();
  await expect(sentence).toHaveText(new RegExp(`^Analysed releases: 6 \\(${unitName}\\)`));
  await expect(sentence).toContainText("Shown: 5 of them (Peer-reviewed publication).");
  await expect(views.locator(".analysis-median")).toHaveText("350");
  await expect(views.getByText("Median of the shown releases: 300 (5 with a value).")).toBeVisible();
  expect(page.url()).toContain("a_type=all");

  // Shown narrows the points, never the box.
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Shown, Type: Peer-reviewed publication" }).click();
  const types = page.getByRole("group", { name: "Type" });
  await types.getByRole("button", { name: /^Peer-reviewed publication/ }).click();
  await expect(sentence).toContainText("Shown: all of them.");
  await types.getByRole("button", { name: /^Feature story/ }).click();
  await expect(sentence).toContainText("Shown: 1 of them (Feature story).");
  await expect(views.locator(".analysis-median")).toHaveText("350");
  await expect(views.getByText("Median of the shown releases: 900 (1 with a value).")).toBeVisible();

  await page.getByRole("button", { name: "Reset" }).click();
  await expect(sentence).toHaveText(/^Analysed releases: \d+ \(Peer-reviewed publication\)/);
});

test("a dimension page: ranked, sorted by another column, exported with both filters", async ({ page }) => {
  const word = tag();
  const { unit } = await releases(word, [
    { title: "Banana", views: 300 },
    { title: "Apple", views: 100 },
    { title: "Cherry", views: 500 },
  ]);
  await page.goto(`/analysis/d/ea_views.d28?a_unit=${unit}`);
  const table = page.getByRole("table", { name: "Ranking by EurekAlert views, day 28" });
  await expect(table).toBeVisible();
  const titles = table.locator("tbody .analysis-title-cell a");
  await expect(titles).toHaveText([`Cherry ${word}`, `Banana ${word}`, `Apple ${word}`]);
  await expect(table.locator("tbody tr").first().locator("td").first()).toHaveText("1");

  await table.getByRole("button", { name: "Title" }).click();
  await expect(titles).toHaveText([`Apple ${word}`, `Banana ${word}`, `Cherry ${word}`]);

  await page.getByRole("button", { name: "Export", exact: true }).click();
  const panel = page.getByRole("dialog");
  await panel.getByLabel(/^CSV/).check();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    panel.getByRole("button", { name: "Download" }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/^release_radar_analysis_ea_views_d28_\d{8}\.csv$/);
  const text = (await readFile(await download.path())).toString("utf-8");
  expect(text.charCodeAt(0)).toBe(0xfeff);
  const lines = text.slice(1).trim().split(/\r?\n/);
  expect(lines[0].split(",").slice(0, 3)).toEqual(["Rank", "Code", "Title"]);
  expect(lines).toHaveLength(4);
  expect(lines[1]).toContain(`Cherry ${word}`);

  // The record opens from the title.
  await titles.first().click();
  await expect(page).toHaveURL(/\/data\?view=all&release=/);
});

test("top & bottom 5 keep a provisional release out of the bottom", async ({ page }) => {
  const word = tag();
  const finished = Array.from({ length: 11 }, (_, place) => ({
    title: `Finished ${String(place + 1).padStart(2, "0")}`,
    views: (place + 1) * 10,
  }));
  const { unit } = await releases(word, [...finished, { title: "Recent", views: 1, age: 10 }]);
  await page.goto(`/analysis/top?a_unit=${unit}&by=ea_views.d28`);
  await expect(page.getByRole("heading", { level: 1, name: "Top & bottom 5" })).toBeVisible();
  await expect(page.getByText(/^Ranked by EurekAlert views, day 28\./)).toBeVisible();

  const highest = page.getByRole("table", { name: "The five highest by EurekAlert views, day 28" });
  const lowest = page.getByRole("table", { name: "The five lowest by EurekAlert views, day 28" });
  await expect(highest.locator("tbody tr")).toHaveCount(5);
  await expect(highest.locator("tbody tr").first()).toContainText(`Finished 11 ${word}`);
  await expect(lowest.locator("tbody tr")).toHaveCount(5);
  // Lowest first: the provisional release has fewer views than any, and is in neither list.
  await expect(lowest.locator("tbody tr").first()).toContainText(`Finished 01 ${word}`);
  await expect(page.getByText(`Recent ${word}`)).toHaveCount(0);
});

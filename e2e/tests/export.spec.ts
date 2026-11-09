import { readFile } from "node:fs/promises";

import { expect, test, type Page } from "@playwright/test";

import { ADA, ADA_STATE, Api, openData, tag } from "../support";

test.use({ storageState: ADA_STATE });

async function exportCsv(page: Page, language: "English" | "日本語"): Promise<string[][]> {
  await page.getByRole("button", { name: /^(Export|エクスポート)$/ }).click();
  const panel = page.getByRole("dialog");
  await panel.getByLabel(/^CSV/).check();
  await panel.getByLabel(language).check();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    panel.getByRole("button", { name: /^(Download|ダウンロード)$/ }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/^release_radar_releases_.*\.csv$/);
  const text = (await readFile(await download.path())).toString("utf-8");
  // UTF-8 with a byte-order mark, so Excel reads Japanese right (R7.6.2).
  expect(text.charCodeAt(0)).toBe(0xfeff);
  return text
    .slice(1)
    .trim()
    .split(/\r?\n/)
    .map((line) => line.split(","));
}

test("export for a report, in English and in Japanese", async ({ page }) => {
  const word = tag();
  const ada = await Api.signIn(ADA);
  await ada.release(`Exported ${word}`, { release_date: "2026-05-01" });
  await ada.dispose();
  await openData(page, word);

  const english = await exportCsv(page, "English");
  expect(english[0]).toEqual(expect.arrayContaining(["Code", "Title", "Release type"]));
  // As shown: the search narrowed it to this release.
  expect(english).toHaveLength(2);
  const row = Object.fromEntries(english[0].map((name, index) => [name, english[1][index]]));
  expect(row["Title"]).toBe(`Exported ${word}`);
  expect(row["Release type"]).toBe("Peer-reviewed publication");
  expect(row["Academic year"]).toBe("2026");

  const japanese = await exportCsv(page, "日本語");
  expect(japanese[0]).toEqual(expect.arrayContaining(["コード", "タイトル", "リリースの種類"]));
  const jaRow = Object.fromEntries(japanese[0].map((name, index) => [name, japanese[1][index]]));
  // Free text stays as written; list values follow the language (R5.4.5).
  expect(jaRow["タイトル"]).toBe(`Exported ${word}`);
  expect(jaRow["リリースの種類"]).toBe("査読付き論文");
});

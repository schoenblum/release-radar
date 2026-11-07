import { describe, expect, it } from "vitest";

import { isNotApplicable, looksLikeDoi, normaliseDate, parseBoolean } from "./parse";

describe("not applicable", () => {
  it.each(["-", "–", "—", "n/a", "N/A", "NA", " na ", "－", "該当なし"])("reads %s as N/A", (text) => {
    expect(isNotApplicable(text)).toBe(true);
  });

  it.each(["", "0", "none", "1", "-1"])("does not read %s as N/A", (text) => {
    expect(isNotApplicable(text)).toBe(false);
  });
});

describe("dates", () => {
  it.each([
    ["2026-04-09", "2026-04-09"],
    ["2026/4/9", "2026-04-09"],
    ["2026.04.09", "2026-04-09"],
    [" 2026-4-9 ", "2026-04-09"],
    ["２０２６-０４-０９", "2026-04-09"],
    ["2026年4月9日", "2026-04-09"],
    ["9-Apr-26", "2026-04-09"],
    ["4-March-26", "2026-03-04"],
    ["9 Apr 2026", "2026-04-09"],
  ])("reads %s", (text, iso) => {
    expect(normaliseDate(text)).toBe(iso);
  });

  it.each(["4/9/2026", "someday", "2026-13-01", "2026-02-30", "32-Jan-26"])(
    "passes %s on unchanged, for the server to explain",
    (text) => {
      expect(normaliseDate(text)).toBe(text);
    },
  );
});

describe("yes and no", () => {
  it.each(["y", "YES", "true", "1", "✓", "はい"])("reads %s as yes", (text) => {
    expect(parseBoolean(text)).toBe(true);
  });

  it.each(["", "n", "No", "false", "0", "いいえ"])("reads %s as no", (text) => {
    expect(parseBoolean(text)).toBe(false);
  });

  it("does not guess", () => {
    expect(parseBoolean("maybe")).toBeNull();
  });
});

describe("telling a DOI from a title", () => {
  it.each([
    "10.1038/nature12373",
    "https://doi.org/10.1038/nature12373",
    "http://dx.doi.org/10.1038/x",
    "doi:10.1038/x",
    "  10.1038/x ",
  ])("%s is a DOI", (text) => {
    expect(looksLikeDoi(text)).toBe(true);
  });

  it.each(["Bees navigate by light", "10 ways to study bees", "10.5 percent of bees"])(
    "%s is a title",
    (text) => {
      expect(looksLikeDoi(text)).toBe(false);
    },
  );
});

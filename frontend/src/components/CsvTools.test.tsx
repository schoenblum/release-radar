import { describe, expect, it } from "vitest";

import type { ImportProblem } from "../api/types";
import i18n, { applyLanguage } from "../i18n";
import { problemMessage } from "./CsvTools";

function problem(values: Partial<ImportProblem>): ImportProblem {
  return { row: 2, key: "Genetics", column: "type", value: "", code: "field_invalid", allowed: [], ...values };
}

describe("an import problem in plain words", () => {
  it("names the row, the column, what was there and what to use instead", async () => {
    await applyLanguage("en");
    const text = problemMessage(
      i18n.t,
      problem({ value: "Research institute", allowed: ["school", "institute", "center", "other"] }),
    );
    expect(text).toBe(
      "Row 2 (Genetics), column “type”: “Research institute” can't be used. " +
        "Please use one of: school, institute, center, other.",
    );
  });

  it("explains a cell with nothing to choose from", async () => {
    await applyLanguage("en");
    const text = problemMessage(
      i18n.t,
      problem({ column: "default_field", value: "Biology", code: "unknown_reference" }),
    );
    expect(text).toContain("“Biology” can't be used. That entry doesn't exist.");
  });

  it("copes with a row that has no key", async () => {
    await applyLanguage("en");
    const text = problemMessage(i18n.t, problem({ key: "", column: "key", code: "field_required" }));
    expect(text).toBe("Row 2 (—), column “key”: This can't be empty.");
  });

  it("speaks of the whole row when no single cell is at fault", async () => {
    await applyLanguage("en");
    const text = problemMessage(i18n.t, problem({ column: null, code: "value_in_use" }));
    expect(text).toBe("Row 2 (Genetics): That's already in use. Please choose another.");
  });

  it("has it in Japanese too", async () => {
    await applyLanguage("ja");
    const text = problemMessage(i18n.t, problem({ value: "x", allowed: ["Y", "N"], column: "active" }));
    expect(text).toContain("2 行目（Genetics）、「active」列");
    expect(text).toContain("Y, N");
    await applyLanguage("en");
  });
});

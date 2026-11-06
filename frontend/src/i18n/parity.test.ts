import { describe, expect, it } from "vitest";

import en from "./locales/en.json";
import ja from "./locales/ja.json";

function keys(node: object, prefix = ""): string[] {
  return Object.entries(node).flatMap(([key, value]) =>
    typeof value === "object" && value !== null
      ? keys(value as object, `${prefix}${key}.`)
      : [`${prefix}${key}`],
  );
}

describe("translation catalogues", () => {
  it("have identical keys in English and Japanese", () => {
    expect(keys(ja).sort()).toEqual(keys(en).sort());
  });
});

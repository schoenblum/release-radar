import { describe, expect, it } from "vitest";

import { parseGender } from "./gender";

describe("reading a gender as typed", () => {
  it.each([
    ["F", "F"],
    ["female", "F"],
    ["Fem", "F"],
    ["  WOMAN ", "F"],
    ["女性", "F"],
    ["女", "F"],
    ["ｆ", "F"],
    ["m", "M"],
    ["Male", "M"],
    ["mal", "M"],
    ["男性", "M"],
    ["other", "other"],
    ["oth", "other"],
    ["x", "other"],
    ["その他", "other"],
  ])("%s is %s", (text, gender) => {
    expect(parseGender(text)).toBe(gender);
  });

  it.each(["", " ", "-", "N/A", "unknown", "Not recorded", "未記録", "不明"])(
    "%s means not recorded",
    (text) => {
      expect(parseGender(text)).toBeNull();
    },
  );

  it.each(["q", "maybe", "17", "fm"])("%s cannot be told", (text) => {
    expect(parseGender(text)).toBeUndefined();
  });
});

import { describe, expect, it } from "vitest";

import { parseClipboard, toClipboard } from "./clipboard";

describe("reading the clipboard", () => {
  it("takes a column of numbers, as from a web table", () => {
    expect(parseClipboard("12\n1,234\n56\n")).toEqual([["12"], ["1,234"], ["56"]]);
  });

  it("takes rows and columns, with Windows line ends", () => {
    expect(parseClipboard("a\tb\r\nc\td\r\n")).toEqual([
      ["a", "b"],
      ["c", "d"],
    ]);
  });

  it("keeps empty cells, as they mean clear or skip", () => {
    expect(parseClipboard("a\t\tc\n\tb")).toEqual([
      ["a", "", "c"],
      ["", "b"],
    ]);
  });

  it("understands how Excel quotes a cell with a line break or a quotation mark", () => {
    expect(parseClipboard('"two\nlines"\tx\n"say ""hi"""\ty')).toEqual([
      ["two\nlines", "x"],
      ['say "hi"', "y"],
    ]);
  });

  it("does not mistake a stray quotation mark for a quoted cell", () => {
    expect(parseClipboard('"not closed\nnext')).toEqual([['"not closed'], ["next"]]);
    expect(parseClipboard('5" screen\tx')).toEqual([['5" screen', "x"]]);
  });

  it("trims spaces, as pasted web tables often carry them", () => {
    expect(parseClipboard("  12 \t 34 ")).toEqual([["12", "34"]]);
  });

  it("treats one value as one cell", () => {
    expect(parseClipboard("42")).toEqual([["42"]]);
  });
});

describe("writing to the clipboard", () => {
  it("quotes only what needs it, and comes back the same", () => {
    const rows = [
      ["plain", "with\ttab"],
      ['a "quote"', "two\nlines"],
    ];
    expect(toClipboard(rows)).toBe('plain\t"with\ttab"\n"a ""quote"""\t"two\nlines"');
    expect(parseClipboard(toClipboard(rows))).toEqual(rows);
  });
});

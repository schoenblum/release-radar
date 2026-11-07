import { describe, expect, it } from "vitest";

import { buildColumns, isVisible } from "./columns";
import { planPaste } from "./paste";
import { context, measure, reading, release } from "./testing";

const MEASURES = [
  measure("a.d0", { position: 0 }),
  measure("b.d0", { position: 1 }),
  measure("web.d28", { position: 2, source: "ga4" }),
];
const columns = buildColumns(context({ measures: MEASURES })).filter((column) =>
  isVisible(column, { hidden: [], shown: [] }),
);
const at = (id: string) => columns.findIndex((column) => column.id === id);
const rows = ["1", "2", "3"].map((id) =>
  release(id, {
    readings: [
      reading("a.d0", { id: `${id}-a` }),
      reading("b.d0", { id: `${id}-b` }),
      reading("web.d28", { id: `${id}-w` }),
    ],
  }),
);
const A = at("measure:a.d0");
const B = at("measure:b.d0");
const WEB = at("measure:web.d28");
const CODE = at("code");
const single = (row: number, column: number) => ({
  top: row,
  bottom: row,
  left: column,
  right: column,
});

describe("planning a paste", () => {
  it("starts a column of numbers at the selected cell", () => {
    const plan = planPaste([["10"], ["20"]], single(1, A), rows, columns);
    expect(plan.saves.map((save) => [save.release.id, save.column.id, save.text])).toEqual([
      ["2", "measure:a.d0", "10"],
      ["3", "measure:a.d0", "20"],
    ]);
    expect(plan).toMatchObject({ problems: [], skipped: 0, overflow: 0 });
  });

  it("fills a selected range with one value", () => {
    const plan = planPaste([["7"]], { top: 0, bottom: 2, left: A, right: B }, rows, columns);
    expect(plan.saves).toHaveLength(6);
    expect(new Set(plan.saves.map((save) => save.text))).toEqual(new Set(["7"]));
  });

  it("takes the room it needs from the top left of a range", () => {
    const plan = planPaste(
      [
        ["1", "2"],
        ["3", "4"],
      ],
      { top: 0, bottom: 2, left: A, right: A },
      rows,
      columns,
    );
    expect(plan.saves.map((save) => [save.release.id, save.column.id, save.text])).toEqual([
      ["1", "measure:a.d0", "1"],
      ["1", "measure:b.d0", "2"],
      ["2", "measure:a.d0", "3"],
      ["2", "measure:b.d0", "4"],
    ]);
  });

  it("skips what cannot be changed here and carries on", () => {
    const plan = planPaste([["1", "2"]], single(0, B), rows, columns);
    expect(columns[WEB].id).toBe("measure:web.d28");
    expect(plan.saves.map((save) => save.column.id)).toEqual(["measure:b.d0"]);
    expect(plan.skipped).toBe(1);
    expect(planPaste([["x"]], single(0, CODE), rows, columns).skipped).toBe(1);
  });

  it("counts what does not fit", () => {
    const plan = planPaste([["1"], ["2"], ["3"], ["4"]], single(1, A), rows, columns);
    expect(plan.saves).toHaveLength(2);
    expect(plan.overflow).toBe(2);
  });

  it("notes a cell it cannot read, which costs only that cell", () => {
    const unit = at("unit");
    const plan = planPaste([["Nowhere"], [""]], single(0, unit), rows, columns);
    expect(plan.problems.map((p) => [p.release.id, p.text, p.code])).toEqual([
      ["1", "Nowhere", "field_invalid"],
    ]);
    expect(plan.saves.map((save) => save.release.id)).toEqual(["2"]);
  });

  it("understands a dash as not applicable, as the team writes it", () => {
    const plan = planPaste([["-"]], single(0, A), rows, columns);
    expect(plan.saves[0].commit).toEqual({
      kind: "reading",
      readingId: "1-a",
      body: { state: "not_applicable" },
    });
  });
});

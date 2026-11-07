import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Reading, Release } from "../../api/types";
import { buildColumns } from "./columns";
import { context, measure, reading, release } from "./testing";
import { useSteadyOrder } from "./useSteadyOrder";
import {
  compareBy,
  filterQuery,
  filtersFrom,
  hasFilters,
  nextSort,
  sortFrom,
  sortText,
  withFilter,
  withoutFilters,
} from "./viewState";

describe("a view in the address", () => {
  it("reads the filters from short names, and ignores what makes no sense", () => {
    const filters = filtersFrom(
      new URLSearchParams("view=all&ay=2025&unit=u1&q=frogs&field=&writer=w1&ay2=x"),
    );
    expect(filters).toEqual({ academic_year: 2025, unit_id: "u1", q: "frogs", writer_id: "w1" });
    expect(filtersFrom(new URLSearchParams("ay=soon")).academic_year).toBeUndefined();
    expect(hasFilters({})).toBe(false);
    expect(hasFilters({ q: "x" })).toBe(true);
  });

  it("changes one filter and keeps the rest, the drawer included", () => {
    const start = new URLSearchParams("view=mine&release=r1&unit=u1");
    const next = withFilter(start, "academic_year", 2026);
    expect(next.toString()).toBe("view=mine&release=r1&unit=u1&ay=2026");
    expect(withFilter(next, "unit_id", null).has("unit")).toBe(false);
    expect(withoutFilters(next).toString()).toBe("view=mine&release=r1");
  });

  it("asks the API in a fixed order, so the same view is cached once", () => {
    expect(filterQuery({ q: "a b", unit_id: "u1", academic_year: 2025 })).toBe(
      "academic_year=2025&unit_id=u1&q=a+b",
    );
    expect(filterQuery({})).toBe("");
  });

  it("sorts up, then down, then not at all", () => {
    expect(nextSort(null, "title")).toEqual({ column: "title", desc: false });
    expect(nextSort({ column: "title", desc: false }, "title")).toEqual({
      column: "title",
      desc: true,
    });
    expect(nextSort({ column: "title", desc: true }, "title")).toBeNull();
    expect(nextSort({ column: "title", desc: true }, "code")).toEqual({
      column: "code",
      desc: false,
    });
    expect(sortFrom(new URLSearchParams("sort=-release_date"))).toEqual({
      column: "release_date",
      desc: true,
    });
    expect(sortText({ column: "code", desc: false })).toBe("code");
  });
});

describe("sorting a column", () => {
  const columns = buildColumns(context({ measures: [measure("views.d0")] }));
  const byId = (id: string) => columns.find((column) => column.id === id)!;
  const views = (id: string, value: number | null, state: Reading["state"] = "value") =>
    release(id, {
      readings: [
        reading("views.d0", {
          value,
          state,
          display_state: state,
        }),
      ],
    });

  it("puts numbers in order and empty ones last, either way round", () => {
    const list = [
      views("a", 30),
      views("b", null, "missing"),
      views("c", 4),
      views("d", null, "not_applicable"),
    ];
    const ascending = [...list].sort(compareBy(byId("measure:views.d0"), false, "en"));
    expect(ascending.map((row) => row.id)).toEqual(["c", "a", "b", "d"]);
    const descending = [...list].sort(compareBy(byId("measure:views.d0"), true, "en"));
    expect(descending.map((row) => row.id)).toEqual(["a", "c", "b", "d"]);
  });

  it("orders codes and words as people expect", () => {
    const list = [
      release("a", { code: "AY2025-10", title: "beta" }),
      release("b", { code: "AY2025-9", title: "Alpha" }),
      release("c", { code: null, title: null }),
    ];
    expect([...list].sort(compareBy(byId("code"), false, "en")).map((r) => r.id)).toEqual([
      "b",
      "a",
      "c",
    ]);
    expect([...list].sort(compareBy(byId("title"), false, "en")).map((r) => r.id)).toEqual([
      "b",
      "a",
      "c",
    ]);
  });
});

describe("rows keep their place", () => {
  const list = (ids: string[], dates: Record<string, string> = {}): Release[] =>
    ids.map((id) => release(id, { release_date: dates[id] ?? "2026-05-01" }));
  const byDate = compareBy(
    buildColumns(context()).find((column) => column.id === "release_date")!,
    false,
    "en",
  );

  it("sorts when the sort is chosen, and an edited row stays where it is", () => {
    const dates = { a: "2026-05-03", b: "2026-05-01", c: "2026-05-02" };
    const { result, rerender } = renderHook(
      ({ key, rows }) => useSteadyOrder(key, rows, true, key.endsWith("sorted") ? byDate : null),
      { initialProps: { key: "all", rows: list(["a", "b", "c"], dates) } },
    );
    expect(result.current.map((row) => row.id)).toEqual(["a", "b", "c"]);
    rerender({ key: "all|sorted", rows: list(["a", "b", "c"], dates) });
    expect(result.current.map((row) => row.id)).toEqual(["b", "c", "a"]);
    // b's date moves past the others: it stays put until the sort is chosen again.
    rerender({ key: "all|sorted", rows: list(["a", "b", "c"], { ...dates, b: "2026-06-01" }) });
    expect(result.current.map((row) => row.id)).toEqual(["b", "c", "a"]);
    // A new release goes on top, a removed one goes.
    rerender({ key: "all|sorted", rows: list(["d", "a", "c"], dates) });
    expect(result.current.map((row) => row.id)).toEqual(["d", "c", "a"]);
  });

  it("waits for the next view's rows before ordering them", () => {
    const { result, rerender } = renderHook(
      ({ key, rows, settled }) => useSteadyOrder(key, rows, settled, null),
      { initialProps: { key: "one", rows: list(["a", "b"]), settled: true } },
    );
    // The previous view's rows, shown while the next one loads.
    rerender({ key: "two", rows: list(["a", "b"]), settled: false });
    expect(result.current.map((row) => row.id)).toEqual(["a", "b"]);
    rerender({ key: "two", rows: list(["c", "a"]), settled: true });
    expect(result.current.map((row) => row.id)).toEqual(["c", "a"]);
  });
});

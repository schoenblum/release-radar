import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { WriterCounts } from "../../api/types";
import { applyLanguage } from "../../i18n";
import WritersPage from "./WritersPage";

const MONTHS = [
  "2025-04",
  "2025-05",
  "2025-06",
  "2025-07",
  "2025-08",
  "2025-09",
  "2025-10",
  "2025-11",
  "2025-12",
  "2026-01",
  "2026-02",
  "2026-03",
];

function counts(...pairs: [number, number][]): number[] {
  const row = Array<number>(12).fill(0);
  for (const [place, count] of pairs) row[place] = count;
  return row;
}

function allYears(): WriterCounts {
  return {
    period: "year",
    academic_year: null,
    academic_years: [2026, 2025],
    columns: ["2025", "2026"],
    rows: [
      {
        writer_id: "w2",
        name_en: "Zed Writer",
        name_ja: null,
        is_active: true,
        counts: [3, 4],
        total: 7,
      },
    ],
    totals: [3, 4],
    total: 7,
    undated: 0,
  };
}

function year(academicYear: number): WriterCounts {
  return {
    period: "month",
    academic_year: academicYear,
    academic_years: [2026, 2025],
    columns: MONTHS,
    rows: [
      {
        writer_id: null,
        name_en: null,
        name_ja: null,
        is_active: true,
        counts: counts([2, 1]),
        total: 1,
      },
      {
        writer_id: "w2",
        name_en: "Zed Writer",
        name_ja: "ゼッド",
        is_active: true,
        counts: counts([0, 2], [11, 1]),
        total: 3,
      },
      {
        writer_id: "w1",
        name_en: "Amy Former",
        name_ja: null,
        is_active: false,
        counts: counts([6, 1]),
        total: 1,
      },
    ],
    totals: counts([0, 2], [2, 1], [6, 1], [11, 1]),
    total: 5,
    undated: 2,
  };
}

function Where() {
  const location = useLocation();
  return <output aria-label="address">{location.pathname + location.search}</output>;
}

function setup(address = "/writers") {
  const fetchMock = vi.fn(async (url: string) => {
    if (url.includes("/export")) {
      return new Response("file", {
        headers: { "Content-Disposition": 'attachment; filename="release_radar_writers_2025.csv"' },
      });
    }
    const asked = /academic_year=(\d{4})/.exec(url)?.[1];
    const body = url.includes("all_years=true") ? allYears() : year(asked ? Number(asked) : 2025);
    return new Response(JSON.stringify(body), {
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  URL.createObjectURL = vi.fn(() => "blob:file");
  URL.revokeObjectURL = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[address]}>
        <Routes>
          <Route path="/writers" element={<WritersPage />} />
          <Route path="/data" element={<p>Data page</p>} />
        </Routes>
        <Where />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  const urls = () => fetchMock.mock.calls.map((call) => String(call[0]));
  return { user: userEvent.setup(), urls };
}

function bodyRows(): HTMLElement[] {
  const [, body] = screen.getAllByRole("rowgroup");
  return within(body).getAllByRole("row");
}

describe("the Writers page", () => {
  beforeEach(() => applyLanguage("en"));
  afterEach(() => vi.unstubAllGlobals());

  it("counts per writer and month, with totals, names in order and no writer last", async () => {
    setup();
    const table = await screen.findByRole("table");
    const headers = within(table)
      .getAllByRole("columnheader")
      .map((cell) => cell.textContent);
    expect(headers).toEqual([
      "Writer",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
      "Jan",
      "Feb",
      "Mar",
      "Total",
    ]);
    expect(bodyRows().map((row) => within(row).getByRole("rowheader").textContent)).toEqual([
      "Amy Former",
      "Zed Writer",
      "No writer yet",
    ]);
    const zed = within(bodyRows()[1]).getAllByRole("cell").map((cell) => cell.textContent);
    expect(zed[0]).toBe("2");
    expect(zed[12]).toBe("3");
    const [, , foot] = screen.getAllByRole("rowgroup");
    expect(within(foot).getAllByRole("cell").at(-1)).toHaveTextContent("5");
    expect(screen.getByText(/AY2025, counted by release date/)).toBeInTheDocument();
    expect(screen.getByText(/without a release date \(2\)/)).toBeInTheDocument();
    // Someone who has left is marked as such.
    expect(within(bodyRows()[0]).getByRole("rowheader")).toHaveAttribute(
      "title",
      "No longer active in the writers list",
    );
  });

  it("links a name to that writer's releases of the year on the Data page", async () => {
    setup();
    const link = await screen.findByRole("link", { name: "Zed Writer" });
    expect(link).toHaveAttribute("href", "/data?view=all&ay=2025&writer=w2");
    // Releases still waiting for a writer are one click away too.
    expect(screen.getByRole("link", { name: "No writer yet" })).toHaveAttribute(
      "href",
      "/data?view=all&ay=2025&writer=none",
    );
    expect(screen.getByRole("link", { name: "Total" })).toHaveAttribute(
      "href",
      "/data?view=all&ay=2025",
    );
  });

  it("keeps the chosen year in the address", async () => {
    const { user, urls } = setup();
    await user.selectOptions(await screen.findByRole("combobox", { name: "Academic year" }), "2026");
    expect(screen.getByRole("status", { name: "address" })).toHaveTextContent("/writers?ay=2026");
    await waitFor(() => expect(urls()).toContain("/api/v1/writers/counts?academic_year=2026"));
    expect(urls()[0]).toBe("/api/v1/writers/counts");
  });

  it("uses Japanese names and months", async () => {
    setup("/writers?ay=2025");
    await screen.findByRole("table");
    await act(async () => applyLanguage("ja"));
    expect(screen.getByRole("columnheader", { name: "4月" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "ゼッド" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "年度" })).toHaveDisplayValue("2025年度");
  });

  it("exports the year shown, as CSV in Japanese", async () => {
    const { user, urls } = setup("/writers?ay=2025");
    await user.click(await screen.findByRole("button", { name: "Export" }));
    expect(screen.getByText(/colleagues' names/)).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: "CSV (UTF-8)" }));
    await user.click(screen.getByRole("radio", { name: "日本語" }));
    await user.click(screen.getByRole("button", { name: "Download" }));
    await waitFor(() =>
      expect(urls()).toContain(
        "/api/v1/writers/counts/export?academic_year=2025&format=csv&language=ja",
      ),
    );
  });

  it("shows all years side by side, and exports them", async () => {
    const { user, urls } = setup("/writers?ay=all");
    await screen.findByRole("table");
    expect(urls()[0]).toBe("/api/v1/writers/counts?all_years=true");
    expect(screen.getByRole("combobox", { name: "Academic year" })).toHaveDisplayValue("All years");
    expect(screen.getByRole("columnheader", { name: "AY2025" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "AY2026" })).toBeInTheDocument();
    expect(screen.getByText(/per writer and academic year/)).toBeInTheDocument();
    // Across all years, a name shows all of that writer's releases.
    expect(screen.getByRole("link", { name: "Zed Writer" })).toHaveAttribute(
      "href",
      "/data?view=all&writer=w2",
    );
    await user.click(screen.getByRole("button", { name: "Export" }));
    await user.click(screen.getByRole("button", { name: "Download" }));
    await waitFor(() =>
      expect(urls()).toContain("/api/v1/writers/counts/export?all_years=true&format=xlsx&language=en"),
    );
  });

  it("offers All years in the year menu", async () => {
    setup();
    const menu = await screen.findByRole("combobox", { name: "Academic year" });
    expect(within(menu).getAllByRole("option").map((option) => option.textContent)).toEqual([
      "All years",
      "AY2026",
      "AY2025",
    ]);
  });
});

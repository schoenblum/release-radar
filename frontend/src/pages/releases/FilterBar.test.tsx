import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ReleaseFilters, Writer } from "../../api/types";
import { applyLanguage } from "../../i18n";
import FilterBar from "./FilterBar";
import { context, coreFields, FEATURE, PAPER, RETIRED, UNIT } from "./testing";

const WRITER: Writer = {
  id: "writer-1",
  display_name_en: "Writer One",
  display_name_ja: null,
  full_name: null,
  is_active: true,
  user_id: null,
  field_versions: {},
} as Writer;

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
}

/** The page's part: the filters live in the address, here in state. */
function Stateful() {
  const [filters, setFilters] = useState<ReleaseFilters>({});
  return (
    <FilterBar
      filters={filters}
      years={[]}
      showWriter
      context={context()}
      onChange={(key, value) => setFilters((current) => ({ ...current, [key]: value ?? undefined }))}
      onClear={() => setFilters({})}
    />
  );
}

function setup(filters: ReleaseFilters = {}, showWriter = true, typeHidden = false) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.includes("/researchers/r-1")) return json({ id: "r-1", name: "Ada Example" });
      return json({
        items: [
          { id: "r-2", name: "Bo Example", current_unit_id: UNIT.id, release_count: 3 },
        ],
        total: 1,
      });
    }),
  );
  const onChange = vi.fn();
  const onClear = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <FilterBar
        filters={filters}
        years={[2026, 2025]}
        showWriter={showWriter}
        context={context({
          writers: [WRITER],
          releaseTypes: [PAPER, FEATURE, RETIRED],
          coreFields: coreFields({
            release_type: typeHidden ? { in_record: false, in_grid: false } : {},
          }),
        })}
        onChange={onChange}
        onClear={onClear}
      />
    </QueryClientProvider>,
  );
  return { onChange, onClear, user: userEvent.setup() };
}

describe("the filters", () => {
  beforeEach(() => applyLanguage("en"));
  afterEach(() => vi.unstubAllGlobals());

  it("each choice is one pick, in the institution's words", async () => {
    const { onChange, user } = setup();
    const year = screen.getByRole("combobox", { name: "Academic year" });
    expect(within(year).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Any year",
      "AY2026",
      "AY2025",
    ]);
    await user.selectOptions(year, "AY2025");
    expect(onChange).toHaveBeenCalledWith("academic_year", 2025);
    await user.selectOptions(screen.getByRole("combobox", { name: "Unit" }), "School of Science");
    expect(onChange).toHaveBeenCalledWith("unit_id", UNIT.id);
    await user.selectOptions(screen.getByRole("combobox", { name: "Writer" }), "Any writer");
    expect(onChange).toHaveBeenLastCalledWith("writer_id", null);
  });

  it("offers every active type and releases without one, all of them by default", async () => {
    const { onChange, user } = setup();
    const kind = screen.getByRole("combobox", { name: "Release type" });
    expect(kind).toHaveValue("");
    expect(within(kind).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Any type",
      "Peer-reviewed publication",
      "Feature story",
      "No type",
    ]);
    await user.selectOptions(kind, "Feature story");
    expect(onChange).toHaveBeenCalledWith("release_type_id", FEATURE.id);
    await user.selectOptions(kind, "No type");
    expect(onChange).toHaveBeenLastCalledWith("release_type_id", "none");
  });

  it("has no type filter where Settings hides the type", () => {
    setup({}, true, true);
    expect(screen.queryByRole("combobox", { name: "Release type" })).not.toBeInTheDocument();
  });

  it("years read as 年度 in Japanese", () => {
    applyLanguage("ja");
    setup();
    expect(screen.getByRole("option", { name: "2025年度" })).toBeInTheDocument();
  });

  it("searches after a pause in typing", async () => {
    const { onChange, user } = setup();
    await user.type(screen.getByRole("searchbox"), "frogs");
    expect(onChange).not.toHaveBeenCalled();
    await waitFor(() => expect(onChange).toHaveBeenCalledWith("q", "frogs"));
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it("has no writer choice in Mine, which is the writer already", () => {
    setup({}, false);
    expect(screen.queryByRole("combobox", { name: "Writer" })).not.toBeInTheDocument();
  });

  it("finds a researcher by name and tells namesakes apart", async () => {
    const { onChange, user } = setup();
    await user.type(screen.getByRole("combobox", { name: "Researcher" }), "Exa");
    const option = await screen.findByRole("option", { name: /Bo Example/ });
    expect(option).toHaveTextContent("School of Science");
    await user.keyboard("{Enter}");
    expect(onChange).toHaveBeenCalledWith("researcher_id", "r-2");
  });

  it("shows a chosen researcher by name, removable in one click, and Clear for all", async () => {
    const { onChange, onClear, user } = setup({ researcher_id: "r-1", q: "maps" });
    expect(await screen.findByText(/Ada Example/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Stop filtering by Ada Example/ }));
    expect(onChange).toHaveBeenCalledWith("researcher_id", null);
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(onClear).toHaveBeenCalled();
  });

  it("Clear empties the search box too", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <Stateful />
      </QueryClientProvider>,
    );
    const user = userEvent.setup();
    await user.type(screen.getByRole("searchbox"), "maps{Enter}");
    await user.click(await screen.findByRole("button", { name: "Clear filters" }));
    expect(screen.getByRole("searchbox")).toHaveValue("");
    expect(screen.queryByRole("button", { name: "Clear filters" })).not.toBeInTheDocument();
  });

  it("offers Clear only when something is chosen", () => {
    setup();
    expect(screen.queryByRole("button", { name: "Clear filters" })).not.toBeInTheDocument();
  });
});

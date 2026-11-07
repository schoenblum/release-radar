import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../components/Toast";
import { applyLanguage } from "../i18n";
import Researchers from "./Researchers";

vi.mock("../auth", () => ({ useAuth: () => ({ user: { role: "editor" } }) }));
vi.mock("../brand", () => ({ useBrand: () => ({ timezone: "Asia/Tokyo" }) }));

const RECORD = {
  merged_into_id: null,
  given_name: null,
  family_name: null,
  name_ja: null,
  current_unit_id: null,
  gender: "not_recorded",
  researchmap_id: null,
  orcid: null,
  status: "incomplete",
  notes: null,
  created_at: "2026-11-07T00:00:00Z",
  field_versions: {},
  merged_count: 0,
};
const ONE = { ...RECORD, id: "one", name: "Test Person", release_count: 2, same_name_count: 1 };
const TWO = { ...RECORD, id: "two", name: "Test Person", release_count: 0, same_name_count: 1 };
const DETAIL = {
  ...ONE,
  merged_count: 1,
  releases: [
    { id: "r1", code: "AY2026-01", title: "Bees", paper_title: null, release_date: "2026-05-01" },
    { id: "r2", code: null, title: null, paper_title: "Ants in detail", release_date: null },
  ],
  merged_records: [
    { id: "gone", name: "T. Person", updated_at: "2026-10-01T00:00:00Z", release_count: 1 },
  ],
};

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function requests(mock: ReturnType<typeof vi.fn>, method: string): [string, unknown][] {
  return mock.mock.calls
    .filter(([, init]) => (init as RequestInit | undefined)?.method === method)
    .map(([url, init]) => [
      String(url),
      JSON.parse(String((init as RequestInit).body ?? "null")) as unknown,
    ]);
}

function renderPage(): void {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <ToastProvider>
        <Researchers />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("telling researchers apart, and splitting them", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    await applyLanguage("en");
    fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "DELETE") return Promise.resolve(new Response(null, { status: 204 }));
      if (init?.method === "POST") return Promise.resolve(json({ source: ONE, target: TWO, created: true }));
      if (url.includes("/researchers/one")) return Promise.resolve(json(DETAIL));
      if (url.includes("/lists/units")) return Promise.resolve(json([]));
      return Promise.resolve(json({ items: [ONE, TWO], total: 2 }));
    });
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("marks namesakes, and the label finds them", async () => {
    const user = userEvent.setup();
    renderPage();
    const labels = await screen.findAllByRole("button", { name: /Others with this name: 1/ });
    expect(labels).toHaveLength(2);
    await user.click(labels[0]);
    expect(screen.getByRole("searchbox")).toHaveValue("Test Person");
  });

  it("offers Split only where there is something to split", async () => {
    renderPage();
    await screen.findByRole("button", { name: "Split" });
    const rows = screen.getAllByRole("row");
    expect(within(rows[1]).getByRole("button", { name: "Split" })).toBeInTheDocument();
    expect(within(rows[2]).queryByRole("button", { name: "Split" })).toBeNull();
  });

  it("moves the ticked releases to a new record of the same name", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: "Split" }));
    // A release without a title or a code is still recognisable.
    expect(await screen.findByText(/\(no code yet\) · Ants in detail/)).toBeInTheDocument();
    await user.click(screen.getByRole("checkbox", { name: /AY2026-01 · 2026-05-01 · Bees/ }));

    expect(screen.getByLabelText("Name of the new record")).toHaveValue("Test Person");
    await user.type(screen.getByLabelText(/How to tell them apart/), "Marine biology");
    await user.click(screen.getByRole("button", { name: "Move selected (1)" }));

    await waitFor(() =>
      expect(requests(fetchMock, "POST")).toContainEqual([
        expect.stringContaining("/researchers/one/split"),
        { release_ids: ["r1"], name: "Test Person", notes: "Marine biology" },
      ]),
    );
    expect(await screen.findByRole("button", { name: "Undo" })).toBeInTheDocument();
  });

  it("undoes a split by moving the release back and removing the record it made", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: "Split" }));
    await user.click(await screen.findByRole("checkbox", { name: /Bees/ }));
    await user.click(screen.getByRole("button", { name: "Move selected (1)" }));
    await user.click(await screen.findByRole("button", { name: "Undo" }));
    await waitFor(() =>
      expect(requests(fetchMock, "DELETE").map(([url]) => url)).toContainEqual(
        expect.stringContaining("/researchers/two"),
      ),
    );
    expect(requests(fetchMock, "POST")).toContainEqual([
      expect.stringContaining("/researchers/two/split"),
      { release_ids: ["r1"], into_id: "one" },
    ]);
  });

  it("lists what was merged in, and can undo that later", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: "Split" }));
    expect(await screen.findByText(/T\. Person, merged on 2026-10-01 \(releases: 1\)/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Undo merge" }));
    await waitFor(() =>
      expect(requests(fetchMock, "POST").map(([url]) => url)).toContainEqual(
        expect.stringContaining("/researchers/gone/unmerge"),
      ),
    );
  });
});

describe("the side panel", () => {
  beforeEach(async () => {
    await applyLanguage("en");
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) =>
        Promise.resolve(
          json(url.includes("/lists/units") ? [] : url.includes("/one") ? DETAIL : { items: [ONE], total: 1 }),
        ),
      ),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("opens outside the table, so sideways scrolling cannot carry it away, and Esc closes it", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: "Split" }));
    const panel = await screen.findByRole("dialog");
    expect(panel.closest("table")).toBeNull();
    expect(panel).toHaveFocus();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });
});

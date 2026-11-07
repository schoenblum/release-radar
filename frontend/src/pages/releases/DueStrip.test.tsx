import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { DueItem } from "../../api/types";
import { applyLanguage } from "../../i18n";
import DueStrip from "./DueStrip";

function item(id: string, changes: Partial<DueItem> = {}): DueItem {
  return {
    kind: "reading",
    release_id: `release-${id}`,
    release_code: `AY2026-${id}`,
    release_title: `Release ${id}`,
    due_date: "2026-05-01",
    due_now: true,
    label_en: "Views",
    label_ja: "閲覧数",
    version: 3,
    reading_id: `reading-${id}`,
    measure_key: "views.d28",
    measure_unit: "views",
    field_key: null,
    field_type: null,
    ...changes,
  };
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function setup(items: DueItem[], patch: (url: string, body: unknown) => Response = () => json({})) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === "PATCH") return patch(url, JSON.parse(String(init.body)));
    return json(items);
  });
  vi.stubGlobal("fetch", fetchMock);
  const onOpen = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <DueStrip onOpen={onOpen} />
    </QueryClientProvider>,
  );
  const saved = () =>
    fetchMock.mock.calls
      .filter(([, init]) => init?.method === "PATCH")
      .map(([url, init]) => [url, JSON.parse(String(init?.body))]);
  return { user: userEvent.setup(), onOpen, saved };
}

describe("what is due", () => {
  beforeEach(() => applyLanguage("en"));
  afterEach(() => vi.unstubAllGlobals());

  it("says so kindly when nothing is", async () => {
    setup([]);
    expect(await screen.findByText(/All caught up/)).toBeInTheDocument();
  });

  it("types a number, saves on Enter, and has the next one ready", async () => {
    const { user, saved } = setup([item("1"), item("2")]);
    const first = await screen.findByRole("textbox", { name: /Release 1/ });
    await user.click(first);
    await user.keyboard("1,234{Enter}");
    await waitFor(() => expect(screen.getByRole("textbox", { name: /Release 2/ })).toHaveFocus());
    await waitFor(() => expect(saved()).toHaveLength(1));
    expect(saved()[0]).toEqual([
      expect.stringContaining("/readings/reading-1"),
      { value: "1,234", version: 3 },
    ]);
  });

  it("Enter on an empty item just moves on", async () => {
    const { user, saved } = setup([item("1"), item("2")]);
    await user.click(await screen.findByRole("textbox", { name: /Release 1/ }));
    await user.keyboard("{Enter}");
    expect(screen.getByRole("textbox", { name: /Release 2/ })).toHaveFocus();
    expect(saved()).toEqual([]);
  });

  it("N/A answers it", async () => {
    const { user, saved } = setup([item("1")]);
    await user.click(await screen.findByRole("button", { name: "N/A" }));
    await waitFor(() => expect(saved()).toHaveLength(1));
    expect(saved()[0][1]).toEqual({ state: "not_applicable", version: 3 });
  });

  it("saves a custom field its own way", async () => {
    const { user, saved } = setup([
      item("1", {
        kind: "custom",
        reading_id: null,
        field_key: "clicks",
        field_type: "integer",
        version: 0,
      }),
    ]);
    await user.click(await screen.findByRole("textbox"));
    await user.keyboard("9{Enter}");
    await waitFor(() => expect(saved()).toHaveLength(1));
    expect(saved()[0]).toEqual([
      expect.stringContaining("/releases/release-1/custom/clicks"),
      { value: "9", version: 0 },
    ]);
  });

  it("keeps what cannot be saved, with the reason", async () => {
    const { user } = setup([item("1")], () => json({ detail: "field_invalid" }, 422));
    await user.click(await screen.findByRole("textbox"));
    await user.keyboard("abc{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent("isn't valid");
    expect(screen.getByRole("textbox")).toHaveValue("abc");
  });

  it("marks what is coming up, and never says late", async () => {
    setup([item("1"), item("2", { due_now: false, due_date: "2026-06-03" })]);
    expect(await screen.findByText("Coming up 2026-06-03")).toBeInTheDocument();
    expect(screen.getByText("Due 2026-05-01")).toBeInTheDocument();
    const text = document.body.textContent?.toLowerCase() ?? "";
    expect(text).not.toMatch(/late|overdue/);
  });

  it("opens the release from its title", async () => {
    const { user, onOpen } = setup([item("1")]);
    await user.click(await screen.findByRole("button", { name: /Release 1/ }));
    expect(onOpen).toHaveBeenCalledWith("release-1");
  });

  it("sends a field that needs more room to the drawer", async () => {
    const { user, onOpen } = setup([
      item("1", { kind: "custom", reading_id: null, field_key: "memo", field_type: "long_text" }),
    ]);
    await user.click(await screen.findByRole("button", { name: "Open to fill in" }));
    expect(onOpen).toHaveBeenCalledWith("release-1");
  });
});

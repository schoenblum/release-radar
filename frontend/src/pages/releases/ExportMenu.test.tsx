import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { applyLanguage } from "../../i18n";
import ExportMenu from "./ExportMenu";

function setup() {
  const fetchMock = vi.fn(
    async () =>
      new Response("file", {
        headers: { "Content-Disposition": 'attachment; filename="release_radar_releases_1.csv"' },
      }),
  );
  vi.stubGlobal("fetch", fetchMock);
  URL.createObjectURL = vi.fn(() => "blob:file");
  URL.revokeObjectURL = vi.fn();
  render(<ExportMenu view="all" filters={{ unit_id: "u1" }} order={["b", "a"]} shown={2} />);
  const sent = () =>
    fetchMock.mock.calls.map((call) => {
      const [url, init] = call as unknown as [string, RequestInit];
      return [url, init.method, JSON.parse(String(init.body))];
    });
  return { user: userEvent.setup(), sent };
}

describe("export", () => {
  beforeEach(() => applyLanguage("en"));
  afterEach(() => vi.unstubAllGlobals());

  it("is two clicks for what is shown, as Excel in the page's language", async () => {
    const { user, sent } = setup();
    await user.click(screen.getByRole("button", { name: "Export" }));
    expect(screen.getByText(/personal data/)).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "As shown (2)" })).toBeChecked();
    await user.click(screen.getByRole("button", { name: "Download" }));
    await waitFor(() => expect(sent()).toHaveLength(1));
    expect(sent()[0]).toEqual([
      "/api/v1/releases/export",
      "POST",
      { format: "xlsx", language: "en", filters: { view: "all", unit_id: "u1" }, order: ["b", "a"] },
    ]);
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("offers the page's language, even after it was switched", async () => {
    const { user } = setup();
    await act(async () => applyLanguage("ja"));
    await user.click(await screen.findByRole("button", { name: "エクスポート" }));
    expect(screen.getByRole("radio", { name: "日本語" })).toBeChecked();
  });

  it("can take everything, as CSV, in Japanese", async () => {
    const { user, sent } = setup();
    await user.click(screen.getByRole("button", { name: "Export" }));
    await user.click(screen.getByRole("radio", { name: "Everything" }));
    await user.click(screen.getByRole("radio", { name: "CSV (UTF-8)" }));
    await user.click(screen.getByRole("radio", { name: "日本語" }));
    await user.click(screen.getByRole("button", { name: "Download" }));
    await waitFor(() => expect(sent()).toHaveLength(1));
    expect(sent()[0][2]).toEqual({ format: "csv", language: "ja", order: [] });
  });
});

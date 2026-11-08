import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { WorkbookImportResult } from "../../api/types";
import { applyLanguage } from "../../i18n";
import WorkbookImport from "./WorkbookImport";

const USERS = [
  { id: "u1", email: "owner@example.org", full_name: "Test Owner", role: "editor", is_active: true },
  { id: "u2", email: "viewer@example.org", full_name: "Test Viewer", role: "viewer", is_active: true },
];

function result(committed: boolean): WorkbookImportResult {
  return {
    committed,
    counts: { releases_new: 3 },
    summary: [
      { label: "Rows in the workbook", count: 4 },
      { label: "New releases", count: 3 },
    ],
    levels: { check: 2, dash: 1, info: 5 },
    markdown: "# Report",
    csv: "Kind,Row",
    filename: "release_radar_dry_run_20261108_1200",
  };
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function setup(answer?: (body: Record<string, unknown>) => Response) {
  const posted: Record<string, unknown>[] = [];
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith("/users")) return json(USERS);
    const body = JSON.parse(String(init?.body)) as Record<string, unknown>;
    posted.push(body);
    return answer ? answer(body) : json(result(body.commit === true));
  });
  vi.stubGlobal("fetch", fetchMock);
  URL.createObjectURL = vi.fn(() => "blob:report");
  URL.revokeObjectURL = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <WorkbookImport />
    </QueryClientProvider>,
  );
  return { user: userEvent.setup(), posted };
}

async function pickFiles(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  await user.upload(
    screen.getByLabelText("Press-release workbook (.xlsx)"),
    new File(["list"], "Press release list.xlsx"),
  );
  await user.upload(
    screen.getByLabelText("Intake workbook (.xlsx)"),
    new File(["intake"], "Release Radar intake.xlsx"),
  );
}

describe("importing the old workbook", () => {
  beforeEach(() => applyLanguage("en"));
  afterEach(() => vi.unstubAllGlobals());

  it("checks first, with the files and the owners chosen, and shows what would happen", async () => {
    const { user, posted } = setup();
    expect(screen.getByRole("button", { name: "Check" })).toBeDisabled();
    await pickFiles(user);
    const bitly = screen.getByRole("combobox", { name: "Bitly clicks, 28 days" });
    // Viewers own no personal fields.
    await waitFor(() => expect(bitly).toHaveTextContent("Test Owner"));
    expect(bitly).not.toHaveTextContent("Test Viewer");
    await user.selectOptions(bitly, "u1");
    await user.click(screen.getByRole("button", { name: "Check" }));

    await screen.findByText("What an import would do (nothing has changed yet)");
    expect(posted[0]).toMatchObject({
      release_list: { name: "Press release list.xlsx", content: btoa("list") },
      intake: { name: "Release Radar intake.xlsx", content: btoa("intake") },
      owners: { bitly: "u1", pitches: null, request_received: null },
      commit: false,
      language: "en",
    });
    expect(screen.getByText("New releases").nextSibling).toHaveTextContent("3");
    expect(screen.getByText(/To check: 2/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Report (CSV)" }));
    expect(URL.createObjectURL).toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Import" }));
    await screen.findByText("Imported");
    expect(posted[1]).toMatchObject({ commit: true, owners: { bitly: "u1" } });
  });

  it("offers Import only for what was checked", async () => {
    const { user } = setup();
    await pickFiles(user);
    await user.click(screen.getByRole("button", { name: "Check" }));
    await screen.findByRole("button", { name: "Import" });
    await user.selectOptions(screen.getByRole("combobox", { name: "Pitches" }), "u1");
    expect(screen.getByRole("button", { name: "Import" })).toBeDisabled();
    expect(screen.getByText(/check again first/)).toBeInTheDocument();
  });

  it("names a missing column", async () => {
    const { user } = setup(() =>
      json({ detail: "import_column_missing", column: "DOI", group: "" }, 422),
    );
    await pickFiles(user);
    await user.click(screen.getByRole("button", { name: "Check" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "A column the import needs is missing. Missing column: DOI.",
    );
  });
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { WorkbookImportResult } from "../../api/types";
import { applyLanguage } from "../../i18n";
import WorkbookImport from "./WorkbookImport";

vi.mock("../../brand", () => ({
  useBrand: () => ({ timezone: "Asia/Tokyo" }),
}));

const USERS = [
  {
    id: "u1",
    email: "owner@example.org",
    full_name: "Test Owner",
    role: "editor",
    is_active: true,
  },
  {
    id: "u2",
    email: "viewer@example.org",
    full_name: "Test Viewer",
    role: "viewer",
    is_active: true,
  },
];

const COLUMNS: WorkbookImportResult["columns"] = [
  {
    key: "28 day engagements",
    heading: "28 day engagements",
    group: "Bitly",
    examples: ["40", "12"],
    suggested_type: "integer",
    fills: [],
    known: false,
  },
  {
    key: "Pitches",
    heading: "Pitches",
    group: "",
    examples: ["3"],
    suggested_type: "integer",
    fills: [{ label: "Pitches", owner: "Test Owner" }],
    known: true,
  },
];

function result(committed: boolean): WorkbookImportResult {
  return {
    columns: COLUMNS,
    run_id: committed ? "run-import" : "run-check",
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

const RUN = {
  id: "run1",
  created_at: "2026-11-08T03:00:00Z",
  committed: true,
  file_names: ["Press release list.xlsx", "Release Radar intake.xlsx"],
  user_name: "Test Owner",
  counts: { releases_new: 112, releases_updated: 0 },
  levels: { check: 36, dash: 42, info: 147 },
};

function setup(
  answer?: (body: Record<string, unknown>) => Response,
  runs: unknown[] = [],
) {
  const posted: Record<string, unknown>[] = [];
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith("/users")) return json(USERS);
    if (url.includes("/imports?kind=")) return json(runs);
    if (url.includes("/report")) {
      return new Response("# Report", {
        headers: {
          "Content-Disposition":
            'attachment; filename="release_radar_import_1.md"',
        },
      });
    }
    const body = JSON.parse(String(init?.body)) as Record<string, unknown>;
    posted.push(body);
    return answer ? answer(body) : json(result(body.commit === true));
  });
  vi.stubGlobal("fetch", fetchMock);
  URL.createObjectURL = vi.fn(() => "blob:report");
  URL.revokeObjectURL = vi.fn();
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <WorkbookImport />
    </QueryClientProvider>,
  );
  const urls = () => fetchMock.mock.calls.map((call) => String(call[0]));
  return { user: userEvent.setup(), posted, urls };
}

async function pickFiles(
  user: ReturnType<typeof userEvent.setup>,
  withIntake = true,
): Promise<void> {
  await user.upload(
    screen.getByLabelText("Press-release workbook (.xlsx)"),
    new File(["list"], "Press release list.xlsx"),
  );
  if (withIntake) {
    await user.upload(
      screen.getByLabelText("Intake workbook (.xlsx), for the first import"),
      new File(["intake"], "Release Radar intake.xlsx"),
    );
  }
}

describe("importing the old workbook", () => {
  beforeEach(() => applyLanguage("en"));
  afterEach(() => vi.unstubAllGlobals());

  it("shows Check and Import from the start, and Import once checked", async () => {
    const { user, posted } = setup();
    // Daniel looked for Import (2026-11-12): it is there, waiting for a check.
    expect(screen.getByRole("button", { name: "Check" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Import" })).toBeDisabled();
    expect(
      screen.getByText(/Import is ready after a check/),
    ).toBeInTheDocument();
    await pickFiles(user);
    await user.click(screen.getByRole("button", { name: "Check" }));

    await screen.findByText(
      "What an import would do (nothing has changed yet)",
    );
    expect(posted[0]).toMatchObject({
      release_list: { name: "Press release list.xlsx", content: btoa("list") },
      intake: { name: "Release Radar intake.xlsx", content: btoa("intake") },
      columns: [],
      commit: false,
      language: "en",
    });
    expect(screen.getByText("New releases").nextSibling).toHaveTextContent("3");
    expect(screen.getByText(/To check: 2/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Report (CSV)" }));
    expect(URL.createObjectURL).toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Import" }));
    await screen.findByText("Imported");
    expect(posted[1]).toMatchObject({ commit: true });
  });

  it("imports again without the intake workbook", async () => {
    const { user, posted } = setup();
    await pickFiles(user, false);
    await user.click(screen.getByRole("button", { name: "Check" }));
    await screen.findByText(
      "What an import would do (nothing has changed yet)",
    );
    expect(posted[0]).toMatchObject({ intake: null });
  });

  it("asks what a column with no field becomes, and checks again with the choice", async () => {
    const { user, posted } = setup();
    await pickFiles(user);
    await user.click(screen.getByRole("button", { name: "Check" }));
    expect(
      await screen.findByText("Other columns in the workbook"),
    ).toBeInTheDocument();
    expect(screen.getByText("For example: 40 · 12")).toBeInTheDocument();
    // A column a field remembers fills it again, with nothing to choose.
    expect(
      screen.getByText("Pitches → Pitches (Test Owner)"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Import" })).toBeEnabled();

    await user.selectOptions(
      screen.getByRole("combobox", {
        name: "What 28 day engagements (Bitly) becomes",
      }),
      "personal",
    );
    expect(
      screen.getByRole("combobox", {
        name: "What 28 day engagements (Bitly) holds",
      }),
    ).toHaveValue("integer");
    const people = screen.getByRole("group", {
      name: "Whose private field 28 day engagements (Bitly) becomes",
    });
    // Viewers enter no data, so they own no fields.
    expect(people).not.toHaveTextContent("Test Viewer");
    await user.click(screen.getByRole("checkbox", { name: "Test Owner" }));
    expect(screen.getByRole("button", { name: "Import" })).toBeDisabled();
    expect(
      screen.getByText(/The files or choices changed since the check/),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Check again" }));
    await waitFor(() => expect(posted).toHaveLength(2));
    expect(posted[1]).toMatchObject({
      commit: false,
      columns: [
        {
          key: "28 day engagements",
          action: "personal",
          field_type: "integer",
          owners: ["u1"],
        },
      ],
    });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Import" })).toBeEnabled(),
    );
  });

  it("sends Only fill what is empty, and a change of it asks for a new check", async () => {
    const { user, posted } = setup();
    await pickFiles(user);
    const fill = screen.getByRole("checkbox", {
      name: /Only fill what is empty/,
    });
    expect(fill).not.toBeChecked();
    await user.click(fill);
    await user.click(screen.getByRole("button", { name: "Check" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Import" })).toBeEnabled(),
    );
    expect(posted[0]).toMatchObject({ fill_empty_only: true, commit: false });
    await user.click(fill);
    expect(screen.getByRole("button", { name: "Import" })).toBeDisabled();
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

  it("lists the checks and imports so far, each report ready to download again", async () => {
    const { user, urls } = setup(undefined, [RUN]);
    const row = (
      await screen.findByText("112 new, 0 updated, 36 to check")
    ).closest("tr");
    expect(row).toHaveTextContent("Import");
    expect(row).toHaveTextContent("Test Owner");
    expect(row).toHaveTextContent("2026-11-08 12:00");
    await user.click(screen.getByRole("button", { name: "CSV" }));
    await waitFor(() =>
      expect(urls()).toContain(
        "/api/v1/imports/run1/report?format=csv&language=en",
      ),
    );
  });
});

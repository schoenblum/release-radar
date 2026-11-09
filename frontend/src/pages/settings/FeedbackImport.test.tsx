import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { WorkbookImportResult } from "../../api/types";
import { applyLanguage } from "../../i18n";
import FeedbackImport from "./FeedbackImport";

vi.mock("../../brand", () => ({ useBrand: () => ({ timezone: "Asia/Tokyo" }) }));

function result(committed: boolean): WorkbookImportResult {
  return {
    run_id: committed ? "run-import" : "run-check",
    committed,
    counts: { feedback_new: 61 },
    summary: [
      { label: "Responses in the file", count: 63 },
      { label: "New responses", count: 61 },
    ],
    levels: { check: 1, info: 20 },
    markdown: "# Researcher feedback import",
    csv: "Kind,Row",
    filename: "release_radar_feedback_dry_run_20261109_1700",
  };
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function setup(answer?: () => Response) {
  const posted: Record<string, unknown>[] = [];
  const urls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      urls.push(url);
      if (url.includes("/imports?kind=")) return json([]);
      const body = JSON.parse(String(init?.body)) as Record<string, unknown>;
      posted.push(body);
      return answer ? answer() : json(result(body.commit === true));
    }),
  );
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <FeedbackImport />
    </QueryClientProvider>,
  );
  return { user: userEvent.setup(), posted, urls };
}

describe("importing researcher feedback", () => {
  beforeEach(() => applyLanguage("en"));
  afterEach(() => vi.unstubAllGlobals());

  it("checks the Forms export, shows what would happen, then imports it", async () => {
    const { user, posted, urls } = setup();
    expect(urls).toContain("/api/v1/imports?kind=feedback");
    expect(screen.getByRole("button", { name: "Check" })).toBeDisabled();
    await user.upload(
      screen.getByLabelText("Microsoft Forms export (.xlsx)"),
      new File(["forms"], "Press release feedback form.xlsx"),
    );
    await user.click(screen.getByRole("button", { name: "Check" }));
    await screen.findByText("What an import would do (nothing has changed yet)");
    expect(posted[0]).toMatchObject({
      file: { name: "Press release feedback form.xlsx", content: btoa("forms") },
      commit: false,
      language: "en",
    });
    expect(screen.getByText("To check: 1 · noted on reading: 20")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Import" }));
    await screen.findByText("Imported");
    expect(posted[1]).toMatchObject({ commit: true });
  });

  it("names a column the export lacks", async () => {
    const { user } = setup(() =>
      json({ detail: "import_column_missing", column: "sat_accuracy", group: "" }, 422),
    );
    await user.upload(
      screen.getByLabelText("Microsoft Forms export (.xlsx)"),
      new File(["forms"], "other.xlsx"),
    );
    await user.click(screen.getByRole("button", { name: "Check" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Missing column: sat_accuracy.");
  });
});

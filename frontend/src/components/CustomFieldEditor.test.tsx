import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CustomField } from "../api/types";
import { applyLanguage } from "../i18n";
import CustomFieldEditor from "./CustomFieldEditor";

const MINE: CustomField = {
  id: "f1",
  key: "clicks",
  label_en: "Clicks",
  label_ja: null,
  help_en: null,
  help_ja: null,
  field_type: "integer",
  options: [],
  vocabulary_id: null,
  scope: "personal",
  owner_id: "me",
  owner_name: "Me Example",
  owner_active: true,
  required: false,
  position: 0,
  is_active: true,
  due_checkpoint_id: null,
  score_eligible: false,
  import_heading: "28 day engagements",
  created_at: "2026-11-12T00:00:00Z",
  field_versions: {},
};

describe("my own fields", () => {
  beforeEach(() => applyLanguage("en"));
  afterEach(() => vi.unstubAllGlobals());

  it("say which workbook column fills them, and can be shared with everyone", async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        calls.push(`${init?.method ?? "GET"} ${url}`);
        const body = url.endsWith("/custom-fields") ? [MINE] : [];
        return new Response(JSON.stringify(body), {
          headers: { "Content-Type": "application/json" },
        });
      }),
    );
    render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <CustomFieldEditor scope="personal" ownerId="me" />
      </QueryClientProvider>,
    );
    expect(
      await screen.findByText("From the workbook column: 28 day engagements"),
    ).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(
      screen.getByRole("button", { name: "Share with everyone" }),
    );
    expect(
      screen.getByText(/It can't be made private again/),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Yes" }));
    await waitFor(() =>
      expect(calls).toContain("POST /api/v1/custom-fields/f1/convert"),
    );
  });
});

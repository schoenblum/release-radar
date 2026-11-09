import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { FeedbackItem, FeedbackResponse } from "../../api/types";
import { applyLanguage } from "../../i18n";
import ResearcherFeedback from "./ResearcherFeedback";

vi.mock("../../brand", () => ({ useBrand: () => ({ timezone: "Asia/Tokyo" }) }));

const item = (key: string, question: FeedbackItem["question"], label: string, extra = {}) =>
  ({
    key,
    question,
    kind: question === "satisfaction" ? "scale" : question === "comments" ? "text" : "flag",
    exclusive: false,
    external: false,
    label_en: label,
    label_ja: `${label}（日本語）`,
    ...extra,
  }) as FeedbackItem;

const ITEMS: FeedbackItem[] = [
  item("inq_media", "inquiries", "Journalists/media", { external: true }),
  item("inq_none", "inquiries", "None", { exclusive: true }),
  item("act_collab", "activities", "Joint research"),
  item("act_none", "activities", "None", { exclusive: true }),
  item("sat_process", "satisfaction", "The production process was easy"),
  item("sat_accuracy", "satisfaction", "It conveyed my research accurately"),
  item("comments", "comments", "Comments"),
];

const RESPONSE: FeedbackResponse = {
  id: "r1",
  source: "legacy_import",
  template_name: "NU Forms 2025",
  submitted_at: "2026-01-05T01:02:00Z",
  language: "ja",
  respondent_name: "Researcher Example",
  answers: { inq_media: true, inq_none: false, sat_process: 5, comments: "Thank you." },
  other_texts: { inquiries: "JST" },
  items: ITEMS,
};

function show(responses: FeedbackResponse[]) {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(JSON.stringify(responses), {
          headers: { "Content-Type": "application/json" },
        }),
    ),
  );
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ResearcherFeedback releaseId="rel-1" />
    </QueryClientProvider>,
  );
}

describe("the record's researcher feedback", () => {
  beforeEach(() => applyLanguage("en"));
  afterEach(() => vi.unstubAllGlobals());

  it("shows each statement in words, what was ticked, and what was skipped", async () => {
    show([RESPONSE]);
    expect(
      await screen.findByText(
        "2026-01-05 · Japanese · Researcher Example · imported from NU Forms 2025",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Strongly agree (5)")).toBeInTheDocument();
    // A statement left blank is not answered, never a 0.
    expect(screen.getAllByText("Not answered")).toHaveLength(2);
    expect(screen.getByText("Journalists/media")).toBeInTheDocument();
    expect(screen.getByText("Other: JST")).toBeInTheDocument();
    expect(screen.getByText("Thank you.")).toBeInTheDocument();
  });

  it("says when there is no feedback yet, in Japanese too", async () => {
    applyLanguage("ja");
    show([]);
    expect(await screen.findByText("まだ回答はありません。")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "研究者アンケート" })).toBeInTheDocument();
  });
});

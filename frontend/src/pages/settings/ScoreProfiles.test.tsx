import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ScoreProfile, ScoreProfileVersion } from "../../api/types";
import { ToastProvider } from "../../components/Toast";
import { applyLanguage } from "../../i18n";
import ScoreProfilesSettings from "./ScoreProfiles";

vi.mock("../../brand", () => ({ useBrand: () => ({ timezone: "Asia/Tokyo" }) }));

const WEIGHTS = { altmetric: 50, "ea_views.d28": 30, "hp_views.d28": 20 };
const V1: ScoreProfileVersion = {
  id: "v1",
  version: 1,
  name_en: "News performance",
  name_ja: "ニュースでの反響",
  purpose: "How far a release travelled.",
  weights: WEIGHTS,
  altmetric_basis: "increase",
  coverage_min: 60,
  comparison_years: 3,
  min_values: 10,
  created_at: "2026-11-12T01:00:00Z",
  created_by: null,
};
const PROFILE: ScoreProfile = {
  id: "p1",
  key: "news_performance",
  is_default: true,
  seeded: true,
  current: V1,
  versions: [V1],
};
const COMPONENTS = [
  { key: "altmetric", label_en: "Altmetric", label_ja: "Altmetric", allowed_in_default: true },
  {
    key: "ea_views.d28",
    label_en: "EurekAlert views",
    label_ja: "閲覧数",
    allowed_in_default: true,
  },
  { key: "hp_views.d28", label_en: "Website views", label_ja: "ウェブ", allowed_in_default: true },
  { key: "satisfaction", label_en: "Satisfaction", label_ja: "満足度", allowed_in_default: false },
];
const ROW = (code: string, score: number) => ({
  release_id: code,
  code,
  title: `Synthetic ${code}`,
  score,
  coverage: 1,
  components: ["altmetric"],
});
const TYPES = [
  {
    id: "t-paper",
    key: "peer_reviewed",
    name_en: "Peer-reviewed publication",
    name_ja: null,
    aliases: [],
    position: 0,
    is_active: true,
    field_versions: {},
  },
  {
    id: "t-feature",
    key: "feature",
    name_en: "Feature",
    name_ja: null,
    aliases: [],
    position: 1,
    is_active: true,
    field_versions: {},
  },
];

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function setup() {
  const sent: { method: string; url: string; body: unknown }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      const path = url.replace("/api/v1", "");
      const body = init?.body ? JSON.parse(String(init.body)) : undefined;
      sent.push({ method, url: path, body });
      if (path === "/score-profiles") return json([PROFILE]);
      if (path === "/score-profiles/components") return json(COMPONENTS);
      if (path === "/score-profiles/p1") return json(PROFILE);
      if (path === "/score-profiles/preview") {
        return json({
          edited: [ROW("AY2026-02", 88)],
          saved: [ROW("AY2026-01", 91)],
          saved_version: 1,
        });
      }
      if (path === "/score-profiles/p1/versions") {
        const v2 = { ...V1, ...body, id: "v2", version: 2 };
        return json({ ...PROFILE, current: v2, versions: [v2, V1] });
      }
      if (path === "/settings/institution" && method === "GET") {
        return json({
          analysed_release_type_ids: ["t-paper"],
          shown_release_type_ids: ["t-paper"],
          field_versions: {},
        });
      }
      if (path === "/settings/institution")
        return json({ field: body.field, value: body.value, version: 1 });
      if (path === "/lists/release_types") return json(TYPES);
      return json({}, 404);
    }),
  );
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <ToastProvider>
        <MemoryRouter>
          <ScoreProfilesSettings />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
  return { user: userEvent.setup(), sent };
}

describe("Settings → Score profiles", () => {
  beforeEach(() => {
    applyLanguage("en");
    window.localStorage.clear();
  });
  afterEach(() => vi.unstubAllGlobals());

  it("shows the running total and saves only weights that add up to 100", async () => {
    const { user, sent } = setup();
    const altmetric = await screen.findByLabelText("Altmetric");
    expect(screen.getByText("Total: 100 of 100")).toBeInTheDocument();
    const save = screen.getByRole("button", { name: "Save as a new version" });
    // Nothing changed yet: nothing to save.
    expect(save).toBeDisabled();

    await user.clear(altmetric);
    await user.type(altmetric, "45");
    expect(screen.getByText(/Total: 95 of 100/)).toBeInTheDocument();
    expect(
      screen.getByText("The weights must add up to 100 before you can save."),
    ).toBeInTheDocument();
    expect(save).toBeDisabled();
    // The draft survives a reload.
    expect(window.localStorage.getItem("rr.score-profile-draft.p1")).toContain('"altmetric":45');

    const website = screen.getByLabelText("Website views");
    await user.clear(website);
    await user.type(website, "25");
    expect(save).toBeEnabled();
    await user.click(save);
    await screen.findByText("Saved as version 2.");
    const posted = sent.find((request) => request.url === "/score-profiles/p1/versions");
    expect(posted?.body).toMatchObject({
      weights: { altmetric: 45, "ea_views.d28": 30, "hp_views.d28": 25 },
      altmetric_basis: "increase",
      min_values: 10,
    });
  });

  it("keeps satisfaction out of the seeded default", async () => {
    setup();
    expect(await screen.findByLabelText(/^Satisfaction/)).toBeDisabled();
    expect(
      screen.getByText("Not in the default profile; other profiles can use it."),
    ).toBeInTheDocument();
  });

  it("previews the top 5 under the saved and the edited version", async () => {
    setup();
    expect(await screen.findByText("Saved (version 1)")).toBeInTheDocument();
    const saved = (await screen.findByText(/Synthetic AY2026-01/)).closest("li");
    expect(saved).toHaveTextContent("91 · coverage 100 %");
    expect(await screen.findByText(/Synthetic AY2026-02/)).toBeInTheDocument();
  });

  it("saves where Analysis starts as types are ticked, shown only within analysed", async () => {
    const { user, sent } = setup();
    const analysed = await screen.findByRole("group", { name: "Analysed" });
    const shown = screen.getByRole("group", { name: "Shown" });
    expect(within(shown).getByRole("checkbox", { name: "Feature" })).toBeDisabled();
    await user.click(within(analysed).getByRole("checkbox", { name: "Feature" }));
    await waitFor(() =>
      expect(sent.find((request) => request.method === "PATCH")?.body).toEqual({
        field: "analysed_release_type_ids",
        value: ["t-paper", "t-feature"],
        version: 0,
      }),
    );
  });
});

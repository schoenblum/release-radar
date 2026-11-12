import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  AnalysisCard,
  AnalysisDimension,
  AnalysisEntry,
  AnalysisOptions,
  AnalysisOverview,
  AnalysisScope,
  AnalysisReleases,
  AnalysisTop,
} from "../../api/types";
import { ToastProvider } from "../../components/Toast";
import { applyLanguage } from "../../i18n";
import i18n from "../../i18n";
import AllReleases from "./AllReleases";
import AnalysisLayout from "./AnalysisLayout";
import { toggled } from "./AnalysisFilterBar";
import DimensionPage from "./DimensionPage";
import { scopeSentence } from "./labels";
import Overview from "./Overview";
import { carried, narrowShown, pagePath, withChoice } from "./state";
import TopBottom from "./TopBottom";

const updateMe = vi.fn();
const setUser = vi.fn();
const user = {
  id: "u1",
  role: "viewer",
  preferences: { data_columns: { hidden: [], shown: [] }, analysis_log_scale: [] },
};
vi.mock("../../auth", () => ({ useAuth: () => ({ user, setUser }) }));
vi.mock("../../api/client", async (original) => {
  const actual = await original<typeof import("../../api/client")>();
  return { ...actual, api: { ...actual.api, updateMe: (...args: unknown[]) => updateMe(...args) } };
});

const PAPER = "type-paper";
const FEATURE = "type-feature";
const SCIENCE = "unit-science";

const NOTHING = { type: null, ay: null, unit: null, field: null, emb: null, gender: null };

const OPTIONS: AnalysisOptions = {
  defaults: {
    analysed: { ...NOTHING, type: [PAPER] },
    shown: { ...NOTHING, type: [PAPER] },
  },
  release_types: [
    { value: PAPER, label_en: "Peer-reviewed publication", label_ja: "査読付き論文", short_en: null, count: 108 },
    { value: FEATURE, label_en: "Feature story", label_ja: "特集記事", short_en: null, count: 2 },
  ],
  academic_years: [
    { value: "2026", label_en: null, label_ja: null, short_en: null, count: 40 },
    { value: "2025", label_en: null, label_ja: null, short_en: null, count: 70 },
  ],
  units: [
    { value: SCIENCE, label_en: "Graduate School of Science", label_ja: "理学研究科", short_en: "Science", count: 23 },
    { value: "none", label_en: null, label_ja: null, short_en: null, count: 3 },
  ],
  fields: [],
  embargoed: [
    { value: "1", label_en: null, label_ja: null, short_en: null, count: 30 },
    { value: "0", label_en: null, label_ja: null, short_en: null, count: 80 },
  ],
  genders: [{ value: "not_recorded", label_en: null, label_ja: null, short_en: null, count: 110 }],
  pages: [
    { key: "score", label_en: "Score", label_ja: "スコア" },
    { key: "ea_views.d28", label_en: "EurekAlert views, day 28", label_ja: "EurekAlert 閲覧数（28 日目）" },
  ],
  profiles: [
    {
      id: "p1",
      version: 2,
      name_en: "News performance",
      name_ja: "ニュースでの反響",
      is_default: true,
      altmetric_basis: "increase",
      coverage_min: 60,
      comparison_years: 3,
      min_values: 10,
    },
  ],
};

function scope(params: URLSearchParams): AnalysisScope {
  const unit = params.get("s_unit");
  const allTypes = params.get("a_type") === "all";
  return {
    analysed: { ...NOTHING, type: allTypes ? null : [PAPER] },
    shown: { ...NOTHING, type: allTypes ? null : [PAPER], unit: unit ? unit.split(",") : null },
    analysed_count: allTypes ? 110 : 108,
    shown_count: unit ? 23 : allTypes ? 110 : 108,
    first_year: 2025,
    last_year: 2026,
    profile: OPTIONS.profiles[0],
    altmetric_basis: "increase",
    today: "2026-11-12",
  };
}

function card(key: string, overrides: Partial<AnalysisCard> = {}): AnalysisCard {
  return {
    key,
    dimension: key,
    label_en: key === "score" ? "Score" : "EurekAlert views, day 28",
    label_ja: key === "score" ? "スコア" : "EurekAlert 閲覧数（28 日目）",
    unit: "views",
    decimals: 0,
    box: { low: 43, q1: 109, median: 201, q3: 247, high: 321, n: 94 },
    counts: { value: 94, missing: 12, not_applicable: 2, not_yet_due: 0, insufficient: 0, provisional: 0 },
    points: Array.from({ length: 94 }, (_, place) => ({
      id: `r${place}`,
      code: `AY2025-${place}`,
      title: `Release ${place}`,
      release_date: "2025-10-01",
      value: 43 + place * 3,
      inferred: false,
    })),
    shown_median: 201,
    ...overrides,
  };
}

function entry(code: string, rank: number | null, value: number | null, extra: Partial<AnalysisEntry> = {}): AnalysisEntry {
  return {
    id: `id-${code}`,
    code,
    title: `Title ${code}`,
    release_date: "2025-10-01",
    academic_year: 2025,
    unit_id: SCIENCE,
    field_id: null,
    value,
    state: value === null ? "missing" : "value",
    inferred: false,
    provisional: false,
    rank,
    percentile: value === null ? null : value / 10,
    coverage: null,
    components: [],
    ...extra,
  };
}

function Where() {
  const location = useLocation();
  return <output aria-label="address">{location.pathname + location.search}</output>;
}

function respond(url: string): unknown {
  const parsed = new URL(url, "http://localhost");
  const params = parsed.searchParams;
  if (parsed.pathname.endsWith("/options")) return OPTIONS;
  if (parsed.pathname.endsWith("/overview")) {
    const shown = scope(params);
    const views = card("ea_views.d28", shown.shown_count === 23 ? { points: card("x").points.slice(0, 23), shown_median: 180 } : {});
    return {
      scope: shown,
      cards: [
        card("score", {
          unit: "score",
          counts: { value: 55, missing: 0, not_applicable: 0, not_yet_due: 0, insufficient: 48, provisional: 5 },
        }),
        views,
      ],
      score_years: [
        { year: 2025, median: 48, n: 40, first: "2025-04-03", last: "2026-03-27" },
        { year: 2026, median: 55, n: 15, first: "2026-04-02", last: "2026-10-01" },
      ],
      answers: [
        {
          question: "inquiries",
          years: [
            { year: 2025, respondents: 40 },
            { year: 2026, respondents: 6 },
          ],
          bars: [
            {
              key: "inq_media",
              label_en: "Journalists/media",
              label_ja: "報道機関（記者・放送局など）",
              shares: [
                { year: 2025, count: 18, share: 45 },
                { year: 2026, count: 2, share: 100 / 3 },
              ],
            },
          ],
        },
        {
          question: "activities",
          years: [{ year: 2026, respondents: 6 }],
          bars: [
            {
              key: "act_collab",
              label_en: "Joint research",
              label_ja: "共同研究",
              shares: [{ year: 2026, count: 1, share: 100 / 6 }],
            },
          ],
        },
      ],
    } satisfies AnalysisOverview;
  }
  if (parsed.pathname.includes("/dimensions/")) {
    return {
      scope: scope(params),
      card: card("ea_views.d28", {
        points: [
          ...card("x").points,
          {
            id: "id-AY2025-03",
            code: "AY2025-03",
            title: "Another",
            release_date: "2025-10-01",
            value: 300,
            inferred: false,
          },
        ],
      }),
      rows: [
        entry("AY2025-02", 1, 900),
        entry("AY2025-01", 2, 300, { provisional: true }),
        entry("AY2025-03", 2, 300, { title: "Another" }),
        entry("AY2025-04", null, null),
      ],
    } satisfies AnalysisDimension;
  }
  if (parsed.pathname.endsWith("/releases")) {
    const standing = (value: number | null, difference: number | null) => ({
      value,
      state: value === null ? ("missing" as const) : ("value" as const),
      provisional: false,
      difference,
    });
    return {
      scope: scope(params),
      columns: [
        { key: "score", label_en: "Score", label_ja: "スコア", unit: "score", decimals: 0, median: 50 },
        {
          key: "ea_views.d28",
          label_en: "EurekAlert views, day 28",
          label_ja: "EurekAlert 閲覧数（28 日目）",
          unit: "views",
          decimals: 0,
          median: 200,
        },
      ],
      releases: [
        {
          id: "id-new",
          code: "AY2026-02",
          title: "A new release",
          release_date: "2026-10-01",
          standings: { score: standing(70, 40), "ea_views.d28": standing(150, -25) },
        },
        {
          id: "id-old",
          code: "AY2025-07",
          title: "An older release",
          release_date: "2025-06-01",
          standings: { score: standing(90, 80), "ea_views.d28": standing(null, null) },
        },
      ],
    } satisfies AnalysisReleases;
  }
  if (parsed.pathname.endsWith("/top")) {
    return {
      scope: scope(params),
      key: params.get("dimension") ?? "score",
      label_en: "Score",
      label_ja: "スコア",
      unit: "score",
      decimals: 0,
      highest: [entry("AY2025-09", 1, 95, { coverage: 1, components: ["ea_views.d28"] })],
      lowest: [entry("AY2025-08", 55, 3, { coverage: 0.7, components: ["ea_views.d28"] })],
    } satisfies AnalysisTop;
  }
  throw new Error(`unexpected ${url}`);
}

function setup(address: string) {
  const fetchMock = vi.fn(async (url: string) => {
    if (url.includes("/export")) {
      return new Response("file", {
        headers: { "Content-Disposition": 'attachment; filename="release_radar_analysis.xlsx"' },
      });
    }
    return new Response(JSON.stringify(respond(url)), {
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  URL.createObjectURL = vi.fn(() => "blob:file");
  URL.revokeObjectURL = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <ToastProvider>
        <MemoryRouter initialEntries={[address]}>
          <Routes>
            <Route path="/analysis" element={<AnalysisLayout />}>
              <Route index element={<Overview />} />
              <Route path="releases" element={<AllReleases />} />
              <Route path="top" element={<TopBottom />} />
              <Route path="d/:key" element={<DimensionPage />} />
            </Route>
          </Routes>
          <Where />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
  const urls = () => fetchMock.mock.calls.map((call) => String(call[0]));
  return { actor: userEvent.setup(), urls };
}

const address = () => screen.getByRole("status", { name: "address" }).textContent ?? "";

describe("the address keeps both filters", () => {
  const defaults = OPTIONS.defaults.analysed;

  it("writes nothing for the default and `all` for every value", () => {
    const empty = new URLSearchParams();
    expect(withChoice(empty, "a", "type", [PAPER], defaults).toString()).toBe("");
    expect(withChoice(empty, "a", "type", null, defaults).toString()).toBe("a_type=all");
    expect(withChoice(empty, "s", "unit", [SCIENCE, "none"], defaults).toString()).toBe(
      `s_unit=none%2C${SCIENCE}`,
    );
  });

  it("takes out of shown what analysed no longer includes", () => {
    const params = new URLSearchParams({ s_unit: `${SCIENCE},none` });
    expect(narrowShown(params, "unit", ["none"]).get("s_unit")).toBe("none");
    expect(narrowShown(params, "unit", ["elsewhere"]).has("s_unit")).toBe(false);
    expect(narrowShown(params, "unit", null).get("s_unit")).toBe(`${SCIENCE},none`);
  });

  it("carries only what belongs to Analysis between pages", () => {
    const params = new URLSearchParams({ a_ay: "2025", by: "score", profile: "p2", sort: "x" });
    expect(carried(params).toString()).toBe("a_ay=2025&profile=p2");
    expect(pagePath("ea_views.d28", params)).toBe("/analysis/d/ea_views.d28?a_ay=2025&profile=p2");
  });

  it("toggles a chip: from all to one, then adds and removes", () => {
    expect(toggled(null, "a")).toEqual(["a"]);
    expect(toggled(["a"], "b")).toEqual(["a", "b"]);
    expect(toggled(["a", "b"], "a")).toEqual(["b"]);
    expect(toggled(["a"], "a")).toBeNull();
  });
});

describe("the sentence under the filters", () => {
  it("says what is analysed and what is shown, in both languages", () => {
    const params = new URLSearchParams({ s_unit: SCIENCE });
    const found = scope(params);
    applyLanguage("en");
    expect(scopeSentence(i18n.t, "en", OPTIONS, found)).toBe(
      "Analysed releases: 108 (Peer-reviewed publication), AY2025–AY2026. Shown: 23 of them (Graduate School of Science).",
    );
    expect(scopeSentence(i18n.t, "en", OPTIONS, scope(new URLSearchParams()))).toBe(
      "Analysed releases: 108 (Peer-reviewed publication), AY2025–AY2026. Shown: all of them.",
    );
    applyLanguage("ja");
    expect(scopeSentence(i18n.t, "ja", OPTIONS, found)).toBe(
      "分析対象：108 件（査読付き論文）、2025年度–2026年度。表示：そのうち 23 件（理学研究科）。",
    );
  });
});

describe("the Analysis pages", () => {
  beforeEach(() => {
    applyLanguage("en");
    updateMe.mockReset();
    updateMe.mockResolvedValue(user);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("shows a count card and a card per dimension, the score first, with plain captions", async () => {
    setup("/analysis");
    expect(await screen.findByRole("heading", { level: 1, name: "Overview" })).toBeInTheDocument();
    const cards = screen.getAllByRole("region").filter((region) => region.tagName === "SECTION");
    const names = cards.map((region) => within(region).queryByRole("heading")?.textContent);
    expect(names.filter(Boolean)).toEqual([
      "News performance",
      "EurekAlert views, day 28",
      "Who got in touch",
      "What came of it",
    ]);
    // The score shows over time, with each academic year's median (Daniel, 2026-11-12).
    expect(
      screen.getByText(
        "Each dot is a shown release with a final score, by its release date. Each line is an academic year's median: AY2025 48, AY2026 55.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getAllByText("Half of the analysed releases land between 109 and 247 (the box). The median is 201.")[0],
    ).toBeInTheDocument();
    expect(screen.getByText("94 with a value, 12 missing, 2 not applicable")).toBeInTheDocument();
    expect(
      screen.getByText("55 with a score, 48 with too little data for one, 5 provisional (under 30 days old)"),
    ).toBeInTheDocument();
    // The chart is drawn, with no inline stylesheet (the production CSP refuses one).
    expect(document.querySelectorAll("svg.rr-plot").length).toBeGreaterThan(0);
    expect(document.querySelectorAll("svg style")).toHaveLength(0);
  });

  it("narrows the shown releases from the bar: the address, the request and the sentence follow", async () => {
    const { actor, urls } = setup("/analysis");
    await screen.findByRole("heading", { level: 1, name: "Overview" });
    await actor.click(screen.getByRole("button", { name: "Shown, Unit: All" }));
    await actor.click(screen.getByRole("button", { name: /Graduate School of Science/ }));
    await waitFor(() => expect(address()).toBe(`/analysis?s_unit=${SCIENCE}`));
    await waitFor(() => expect(urls()).toContain(`/api/v1/analysis/overview?s_unit=${SCIENCE}`));
    expect(
      await screen.findByText(/Shown: 23 of them \(Graduate School of Science\)\./),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Half of the analysed releases land between 109 and 247 (the box). Median of the shown releases: 180 (23 with a value).",
      ),
    ).toBeInTheDocument();
    // The filters carry over to every other Analysis page.
    expect(screen.getByRole("link", { name: "Top & bottom 5" })).toHaveAttribute(
      "href",
      `/analysis/top?s_unit=${SCIENCE}`,
    );
    await actor.click(screen.getByRole("button", { name: "Reset" }));
    expect(address()).toBe("/analysis");
  });

  it("analyses every type at a click on All", async () => {
    const { actor } = setup("/analysis");
    await screen.findByRole("heading", { level: 1, name: "Overview" });
    await actor.click(screen.getByRole("button", { name: "Analysed, Type: Peer-reviewed publication" }));
    await actor.click(screen.getByRole("button", { name: "All" }));
    expect(address()).toBe("/analysis?a_type=all");
    expect(await screen.findByText(/Analysed releases: 110, AY2025–AY2026\./)).toBeInTheDocument();
  });

  it("remembers the log scale per card, saving only that preference", async () => {
    const { actor } = setup("/analysis");
    await screen.findByRole("heading", { level: 1, name: "Overview" });
    await actor.click(screen.getByRole("checkbox", { name: "Log scale for EurekAlert views, day 28" }));
    expect(updateMe).toHaveBeenCalledWith({ preferences: { analysis_log_scale: ["ea_views.d28"] } });
    expect(setUser).toHaveBeenCalled();
  });

  it("shows a chart's numbers as a table too", async () => {
    const { actor } = setup("/analysis");
    await screen.findByRole("heading", { level: 1, name: "Overview" });
    const [score, views] = screen.getAllByRole("button", { name: "Show as table" });
    // The score over time: each year's median, then the releases.
    await actor.click(score);
    const years = screen.getAllByRole("table")[0];
    expect(within(years).getByRole("rowheader", { name: "AY2026" })).toBeInTheDocument();
    expect(within(years).getByText("55")).toBeInTheDocument();
    await actor.click(score);
    await actor.click(views);
    const summary = screen.getAllByRole("table")[0];
    expect(within(summary).getByRole("rowheader", { name: "Lower quartile" })).toBeInTheDocument();
    expect(within(summary).getByText("109")).toBeInTheDocument();
  });

  it("ranks a dimension's shown releases, sorts by any column and exports with both filters", async () => {
    const { actor, urls } = setup(`/analysis/d/ea_views.d28?s_unit=${SCIENCE}`);
    expect(
      await screen.findByRole("heading", { level: 1, name: "EurekAlert views, day 28" }),
    ).toBeInTheDocument();
    const table = screen.getByRole("table", { name: "Ranking by EurekAlert views, day 28" });
    const codes = () =>
      within(table)
        .getAllByRole("rowheader")
        .map((cell) => cell.textContent);
    expect(codes()).toEqual(["AY2025-02", "AY2025-01", "AY2025-03", "AY2025-04"]);
    expect(within(table).getAllByText("provisional")).toHaveLength(1);
    expect(within(table).getByRole("link", { name: "Title AY2025-02" })).toHaveAttribute(
      "href",
      "/data?view=all&release=id-AY2025-02",
    );
    await actor.click(within(table).getByRole("button", { name: "Title" }));
    expect(codes()).toEqual(["AY2025-03", "AY2025-01", "AY2025-02", "AY2025-04"]);

    await actor.click(screen.getByRole("button", { name: "Export" }));
    await actor.click(screen.getByRole("radio", { name: "CSV (UTF-8)" }));
    await actor.click(screen.getByRole("button", { name: "Download" }));
    await waitFor(() =>
      expect(urls()).toContain(
        `/api/v1/analysis/dimensions/ea_views.d28/export?s_unit=${SCIENCE}&format=csv&language=en`,
      ),
    );
  });

  it("lists the highest and lowest 5 and switches what they are ranked by", async () => {
    const { actor, urls } = setup("/analysis/top");
    expect(await screen.findByRole("heading", { level: 1, name: "Top & bottom 5" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "The five highest by News performance" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "The five lowest by News performance" })).toBeInTheDocument();
    expect(screen.getAllByText("EurekAlert views, day 28").length).toBeGreaterThan(0);
    await actor.selectOptions(screen.getByRole("combobox", { name: "Ranked by" }), "ea_views.d28");
    expect(address()).toBe("/analysis/top?by=ea_views.d28");
    await waitFor(() => expect(urls()).toContain("/api/v1/analysis/top?dimension=ea_views.d28"));
  });

  it("shows researcher feedback as bars per academic year", async () => {
    setup("/analysis");
    const card = await screen.findByRole("region", { name: "Who got in touch" });
    expect(within(card).getByText("Journalists/media")).toBeInTheDocument();
    expect(within(card).getByText("AY2025: 45% (18 of 40)")).toBeInTheDocument();
    expect(within(card).getByText("AY2026: 33% (2 of 6)")).toBeInTheDocument();
    expect(card.querySelectorAll(".answer-fill")).toHaveLength(2);
    expect(card.querySelector<HTMLElement>(".answer-fill")?.style.width).toBe("45%");
    expect(
      within(card).getByText(/Releases that answered, by academic year: AY2025: 40, AY2026: 6\./),
    ).toBeInTheDocument();
    // One year: no legend, one bar.
    const outcomes = screen.getByRole("region", { name: "What came of it" });
    expect(outcomes.querySelector(".answer-legend")).toBeNull();
    expect(outcomes.querySelectorAll(".answer-fill")).toHaveLength(1);
  });

  it("says which release a clicked point is, with a link to its record", async () => {
    const { actor } = setup("/analysis/d/ea_views.d28");
    await screen.findByRole("heading", { level: 1, name: "EurekAlert views, day 28" });
    const chart = document.querySelector(".rr-chart") as HTMLElement;
    // jsdom lays nothing out: every dot is at 0, 0, so a click there reaches the first.
    expect(chart.querySelectorAll(".rr-pickable circle").length).toBe(95);
    await actor.pointer({ keys: "[MouseLeft]", target: chart, coords: { clientX: 0, clientY: 0 } });
    const window = await screen.findByRole("dialog", { name: "Release 0" });
    expect(within(window).getByRole("link", { name: "Release 0" })).toHaveAttribute(
      "href",
      "/data?view=all&release=r0",
    );
    expect(within(window).getByText("43")).toBeInTheDocument();
    await actor.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens the window of a release named in the address", async () => {
    const { actor } = setup("/analysis/d/ea_views.d28?release=id-AY2025-03");
    const window = await screen.findByRole("dialog", { name: "Another" });
    expect(document.querySelectorAll("circle.rr-picked")).toHaveLength(1);
    // Down to its row in the ranking, on request: arriving, the chart stays in view.
    await actor.click(within(window).getByRole("button", { name: "Show it in the ranking" }));
    const table = screen.getByRole("table", { name: "Ranking by EurekAlert views, day 28" });
    expect(within(table).getByRole("link", { name: "Another" })).toHaveFocus();
  });

  it("marks a release named in the address in the ranking", async () => {
    const { urls } = setup("/analysis/d/ea_views.d28?release=id-AY2025-03");
    const table = await screen.findByRole("table", { name: "Ranking by EurekAlert views, day 28" });
    const row = within(table).getByRole("rowheader", { name: "AY2025-03" }).closest("tr");
    expect(row).toHaveClass("is-picked");
    // The pick stays in the page; the server never hears of it.
    expect(urls().some((url) => url.includes("release="))).toBe(false);
  });

  it("lists all releases against the median, newest first, linking to the record and the measure", async () => {
    const { actor } = setup(`/analysis/releases?s_unit=${SCIENCE}`);
    expect(await screen.findByRole("heading", { level: 1, name: "All releases" })).toBeInTheDocument();
    const table = screen.getByRole("table", { name: /shown releases with their score/ });
    const titles = () =>
      within(table)
        .getAllByRole("rowheader")
        .map((cell) => within(cell).getByRole("link").textContent);
    expect(titles()).toEqual(["A new release", "An older release"]);
    expect(within(table).getByText("Median 200")).toBeInTheDocument();
    expect(within(table).getByRole("link", { name: "A new release" })).toHaveAttribute(
      "href",
      "/data?view=all&release=id-new",
    );
    const views = within(table).getByRole("link", { name: /150/ });
    expect(views).toHaveAttribute(
      "href",
      `/analysis/d/ea_views.d28?s_unit=${SCIENCE}&release=id-new`,
    );
    expect(within(views).getByText("−25%")).toBeInTheDocument();
    expect(within(views).getByText("25% below the median")).toBeInTheDocument();
    expect(within(table).getAllByText("+40%")).toHaveLength(1);
    // Highest score first at a click on its heading.
    await actor.click(within(table).getByRole("button", { name: "News performance" }));
    expect(titles()).toEqual(["An older release", "A new release"]);
  });

  it("speaks Japanese", async () => {
    applyLanguage("ja");
    setup("/analysis");
    expect(await screen.findByRole("heading", { level: 1, name: "概要" })).toBeInTheDocument();
    expect(screen.getByText("値あり 94 件、未入力 12 件、該当なし 2 件")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "上位・下位5件" })).toBeInTheDocument();
  });
});

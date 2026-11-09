import { beforeEach, describe, expect, it } from "vitest";

import { applyLanguage } from "../../i18n";
import { buildColumns, isVisible, toggleColumn, type GridColumn } from "./columns";
import {
  context,
  coreFields,
  customField,
  FEATURE,
  measure,
  PAPER,
  reading,
  release,
  RETIRED,
  UNIT,
} from "./testing";

const MEASURES = [
  measure("ea_views.d0", { position: 0 }),
  measure("altmetric.d0", { position: 1, unit: "score" }),
  measure("hp_views.d28", { position: 2, source: "ga4" }),
  measure("pickups_all", { position: 3, source: "derived", is_active: false }),
];

function find(columns: GridColumn[], id: string): GridColumn {
  const column = columns.find((row) => row.id === id);
  if (!column) throw new Error(`No column ${id}`);
  return column;
}

function shown(columns: GridColumn[]): string[] {
  return columns.filter((column) => isVisible(column, { hidden: [], shown: [] })).map((c) => c.id);
}

describe("which columns there are", () => {
  beforeEach(() => applyLanguage("en"));

  it("shows the default columns of the brief and what analysis tells apart, in order", () => {
    const columns = buildColumns(
      context({ measures: MEASURES, customFields: [customField("clicks")] }),
    );
    // R7.5.2, plus field, type and embargo (Daniel, 2026-11-09).
    expect(shown(columns)).toEqual([
      "code",
      "title",
      "release_date",
      "researcher",
      "researcher_gender",
      "unit",
      "field",
      "release_type",
      "doi",
      "publication_date",
      "measure:ea_views.d0",
      "measure:altmetric.d0",
      "measure:hp_views.d28",
      "embargoed",
      "ea_url",
      "website_url",
      "ea_top_page",
      "custom:clicks",
    ]);
  });

  it("shows a saved link as a mark that opens it, and takes a DOI pasted either way", () => {
    const columns = buildColumns(context());
    const saved = release("1", {
      doi: "10.1234/abc<1>",
      ea_url: "https://www.eurekalert.org/news-releases/1234567",
      website_url: "https://news.example.org/research/frogs",
    });
    expect(find(columns, "doi").view(saved)).toMatchObject({
      text: "✓",
      hint: "10.1234/abc<1>",
      href: "https://doi.org/10.1234/abc%3C1%3E",
    });
    expect(find(columns, "ea_url").view(saved)).toMatchObject({
      text: "✓",
      href: "https://www.eurekalert.org/news-releases/1234567",
    });
    expect(find(columns, "website_url").view(saved).href).toBe(
      "https://news.example.org/research/frogs",
    );
    // A copy gives the address itself.
    expect(find(columns, "ea_url").editText(saved)).toBe(
      "https://www.eurekalert.org/news-releases/1234567",
    );
    // Nothing that is not a web address becomes a link.
    expect(find(columns, "ea_url").view(release("2", { ea_url: "javascript:alert(1)" })).href).toBe(
      undefined,
    );
    expect(find(columns, "doi").view(release("3")).text).toBe("");
    // The server keeps the bare DOI, whichever way it came.
    for (const written of ["10.1234/abc", "https://doi.org/10.1234/abc"]) {
      expect(find(columns, "doi").parse(written, release("4"))).toEqual({
        ok: true,
        commit: { kind: "field", field: "doi", value: written },
      });
    }
  });

  it("offers the active release types and reads a name, an alias or the key", () => {
    const columns = buildColumns(context({ releaseTypes: [PAPER, FEATURE, RETIRED] }));
    const column = find(columns, "release_type");
    expect(column.editor).toBe("select");
    expect(column.options.map((option) => option.label)).toEqual([
      "Peer-reviewed publication",
      "Feature story",
    ]);
    const draft = release("1", { release_type_id: PAPER.id });
    expect(column.view(draft).text).toBe("Peer-reviewed publication");
    // A retired type still shows on the releases that have it.
    expect(column.view(release("2", { release_type_id: RETIRED.id })).text).toBe(
      "Book announcement",
    );
    for (const written of ["feature story", "FEATURE", "Feature story（日本語）"]) {
      expect(column.parse(written, draft)).toEqual({
        ok: true,
        commit: { kind: "field", field: "release_type_id", value: FEATURE.id },
      });
    }
    expect(column.parse("paper", draft)).toMatchObject({ ok: true });
    expect(column.parse("Book announcement", draft)).toEqual({ ok: false, code: "field_invalid" });
    expect(column.parse("", draft)).toEqual({
      ok: true,
      commit: { kind: "field", field: "release_type_id", value: null },
    });
    expect(column.snapshot(draft)).toEqual({
      kind: "field",
      field: "release_type_id",
      value: PAPER.id,
    });
  });

  it("puts the paper's date right after the DOI, wherever Settings puts either", () => {
    const moved = buildColumns(
      context({ coreFields: coreFields({ publication_date: { position: 99 }, doi: { position: 4 } }) }),
    );
    const ids = moved.map((c) => c.id);
    expect(ids.indexOf("publication_date")).toBe(ids.indexOf("doi") + 1);
    // Without a DOI column it still has a place.
    const noDoi = buildColumns(context({ coreFields: coreFields({ doi: { hidden: true } }) }));
    expect(noDoi.map((c) => c.id)).toContain("publication_date");
  });

  it("freezes the first columns and always keeps them", () => {
    const columns = buildColumns(context());
    expect(columns.filter((c) => c.frozen).map((c) => c.id)).toEqual(["code", "title"]);
    expect(columns.filter((c) => c.locked).map((c) => c.id)).toEqual(["code", "title"]);
  });

  it("offers a hidden field to nobody, and uses a label from Settings", () => {
    const columns = buildColumns(
      context({
        coreFields: coreFields({
          journal: { hidden: true },
          doi: { label_en: "Paper ID" },
        }),
      }),
    );
    expect(columns.map((c) => c.id)).not.toContain("journal");
    expect(columns.map((c) => c.id)).not.toContain("title_ja");
    expect(find(columns, "doi").label).toBe("Paper ID");
  });

  it("follows the order set in Settings", () => {
    const columns = buildColumns(
      context({
        coreFields: coreFields({
          unit: { position: 3 },
          researcher: { position: 6 },
        }),
      }),
    );
    const ids = shown(columns);
    expect(ids.indexOf("unit")).toBeLessThan(ids.indexOf("researcher"));
  });

  it("labels a colleague's field with its owner, and it cannot be changed", () => {
    const columns = buildColumns(
      context({ customFields: [customField("theirs", { owner_id: "other", owner_name: "Sam" })] }),
    );
    const column = find(columns, "custom:theirs");
    expect(column.label).toBe("theirs (Sam)");
    expect(column.group).toBe("colleagues");
    expect(column.byDefault).toBe(false);
    expect(column.isEditable(release("1"))).toBe(false);
  });

  it("leaves a retired field out", () => {
    const columns = buildColumns(
      context({ customFields: [customField("old", { is_active: false })] }),
    );
    expect(columns.map((c) => c.id)).not.toContain("custom:old");
  });

  it("uses Japanese names", () => {
    const columns = buildColumns(context({ language: "ja", measures: MEASURES }));
    expect(find(columns, "measure:ea_views.d0").label).toBe("ea_views.d0（日本語）");
    const unit = find(columns, "unit").view(release("1", { unit_id: UNIT.id }));
    expect(unit.text).toBe("理学研究科");
  });
});

describe("what a number cell shows", () => {
  const column = (): GridColumn => find(buildColumns(context({ measures: MEASURES })), "measure:ea_views.d0");
  const withReading = (changes: Parameters<typeof reading>[1]) =>
    release("1", { readings: [reading("ea_views.d0", changes)] });

  beforeEach(() => applyLanguage("en"));

  it("shows a value, and zero is a value", () => {
    const value = column().view(
      withReading({ value: 1234, state: "value", display_state: "value" }),
    );
    expect(value).toMatchObject({ text: "1,234", tone: "plain" });
    const zero = column().view(withReading({ value: 0, state: "value", display_state: "value" }));
    expect(zero).toMatchObject({ text: "0", tone: "plain" });
  });

  it("tints what is due and empty, and says when, without calling it late", () => {
    const cell = column().view(withReading({ display_state: "missing" }));
    expect(cell.tone).toBe("due");
    expect(cell.text).toBe("");
    expect(cell.hint).toBe("Due 2026-05-29");
  });

  it("greys N/A and leaves what is not yet due plain", () => {
    expect(
      column().view(withReading({ state: "not_applicable", display_state: "not_applicable" })),
    ).toMatchObject({ text: "N/A", tone: "na" });
    expect(column().view(withReading({ display_state: "not_yet_due" })).tone).toBe("later");
  });

  it("does not ask anyone for an automatic number, or let it be typed here", () => {
    const auto = find(buildColumns(context({ measures: MEASURES })), "measure:hp_views.d28");
    const row = release("1", { readings: [reading("hp_views.d28")] });
    expect(auto.view(row).tone).toBe("muted");
    expect(auto.isEditable(row)).toBe(false);
    expect(auto.editor).toBe("none");
  });
});

describe("reading what is typed", () => {
  const columns = () =>
    buildColumns(
      context({
        measures: MEASURES,
        customFields: [
          customField("pick", {
            field_type: "single_select",
            options: [{ key: "a", label_en: "Apple", label_ja: "りんご" }],
          }),
          customField("flag", { field_type: "boolean" }),
          customField("day", { field_type: "date" }),
          customField("long", { field_type: "long_text" }),
        ],
      }),
    );
  const row = release("1", { readings: [reading("ea_views.d0", { id: "r1" })] });

  it("sends a number as written, for the server to judge", () => {
    expect(find(columns(), "measure:ea_views.d0").parse("1,234", row)).toEqual({
      ok: true,
      commit: { kind: "reading", readingId: "r1", body: { value: "1,234" } },
    });
  });

  it.each(["-", "N/A"])("takes %s as not applicable", (text) => {
    expect(find(columns(), "measure:ea_views.d0").parse(text, row)).toEqual({
      ok: true,
      commit: { kind: "reading", readingId: "r1", body: { state: "not_applicable" } },
    });
  });

  it("takes nothing as clearing", () => {
    expect(find(columns(), "measure:ea_views.d0").parse("", row)).toEqual({
      ok: true,
      commit: { kind: "reading", readingId: "r1", body: { state: "missing" } },
    });
  });

  it("matches a list entry by any of its names", () => {
    const unit = find(columns(), "unit");
    for (const text of ["School of Science", "理学研究科", "SCI", "science", "Science School"]) {
      expect(unit.parse(text, row)).toEqual({
        ok: true,
        commit: { kind: "field", field: "unit_id", value: "unit-1" },
      });
    }
    expect(unit.parse("Nowhere", row)).toEqual({ ok: false, code: "field_invalid" });
    expect(unit.parse("", row)).toEqual({
      ok: true,
      commit: { kind: "field", field: "unit_id", value: null },
    });
  });

  it("will not guess a researcher from a name, since names are not unique", () => {
    const researcher = find(columns(), "researcher");
    expect(researcher.parse("Test Person", row)).toEqual({
      ok: false,
      code: "researcher_needs_choosing",
    });
    expect(researcher.parse("", row)).toEqual({
      ok: true,
      commit: { kind: "field", field: "researcher_id", value: null },
    });
  });

  it("tidies a date, and reads yes and no", () => {
    expect(find(columns(), "release_date").parse("2026/4/9", row)).toEqual({
      ok: true,
      commit: { kind: "field", field: "release_date", value: "2026-04-09" },
    });
    expect(find(columns(), "ea_top_page").parse("yes", row)).toEqual({
      ok: true,
      commit: { kind: "field", field: "ea_top_page", value: true },
    });
    expect(find(columns(), "ea_top_page").parse("maybe", row)).toEqual({
      ok: false,
      code: "field_invalid",
    });
  });

  it("handles custom fields by type", () => {
    const list = columns();
    expect(find(list, "custom:pick").parse("Apple", row)).toEqual({
      ok: true,
      commit: { kind: "custom", key: "pick", body: { value: "a" } },
    });
    expect(find(list, "custom:day").parse("2026/4/9", row)).toEqual({
      ok: true,
      commit: { kind: "custom", key: "day", body: { value: "2026-04-09" } },
    });
    expect(find(list, "custom:flag").parse("-", row)).toEqual({
      ok: true,
      commit: { kind: "custom", key: "flag", body: { state: "not_applicable" } },
    });
    // Long text needs the drawer's room.
    expect(find(list, "custom:long").editor).toBe("none");
    expect(find(list, "custom:long").isEditable(row)).toBe(false);
  });

  it("refuses to save what cannot be edited, and viewers can edit nothing", () => {
    expect(find(columns(), "code").parse("AY2026-99", row).ok).toBe(false);
    const read = buildColumns(context({ canEdit: false, measures: MEASURES }));
    expect(read.some((column) => column.isEditable(row))).toBe(false);
  });
});

describe("the researcher's gender", () => {
  beforeEach(() => applyLanguage("en"));
  const column = () => find(buildColumns(context()), "researcher_gender");

  it("shows the word, and nothing when it is not recorded", () => {
    expect(column().view(release("1", { researcher_id: "r", researcher_gender: "F" })).text).toBe(
      "Female",
    );
    expect(column().view(release("1", { researcher_id: "r" })).text).toBe("");
  });

  it("reads what is typed as forgivingly as a date", () => {
    const withResearcher = release("1", { researcher_id: "r" });
    expect(column().parse("fem", withResearcher)).toEqual({
      ok: true,
      commit: { kind: "field", field: "researcher_gender", value: "F" },
    });
    expect(column().parse("男性", withResearcher)).toEqual({
      ok: true,
      commit: { kind: "field", field: "researcher_gender", value: "M" },
    });
    expect(column().parse("", withResearcher)).toEqual({
      ok: true,
      commit: { kind: "field", field: "researcher_gender", value: null },
    });
    expect(column().parse("maybe", withResearcher)).toEqual({ ok: false, code: "gender_invalid" });
  });

  it("can be changed only once there is a researcher", () => {
    expect(column().isEditable(release("1"))).toBe(false);
    expect(column().isEditable(release("1", { researcher_id: "r" }))).toBe(true);
    expect(
      find(buildColumns(context({ canEdit: false })), "researcher_gender").isEditable(
        release("1", { researcher_id: "r" }),
      ),
    ).toBe(false);
  });
});

describe("what undo puts back", () => {
  const column = () => find(buildColumns(context({ measures: MEASURES })), "measure:ea_views.d0");
  const snapshot = (changes: Parameters<typeof reading>[1]) =>
    column().snapshot(release("1", { readings: [reading("ea_views.d0", { id: "r", ...changes })] }));

  it("a number comes back as that number", () => {
    expect(snapshot({ value: 5, state: "value" })).toEqual({
      kind: "reading",
      readingId: "r",
      body: { value: 5 },
    });
  });

  it("a person's N/A comes back as N/A, and a rule's goes back to the rules", () => {
    expect(snapshot({ state: "not_applicable", source: "manual" })).toMatchObject({
      body: { state: "not_applicable" },
    });
    expect(snapshot({ state: "not_applicable", source: "auto" })).toMatchObject({
      body: { state: "missing" },
    });
  });

  it("a plain field comes back with its old value", () => {
    const unit = find(buildColumns(context()), "unit");
    expect(unit.snapshot(release("1", { unit_id: "unit-1" }))).toEqual({
      kind: "field",
      field: "unit_id",
      value: "unit-1",
    });
  });
});

describe("a due custom field", () => {
  const CHECKPOINT = {
    id: "d0",
    key: "d0",
    label_en: "Day 0",
    label_ja: null,
    offset_days: 0,
    remind_days_before: 0 as const,
    field_versions: {},
  };
  const column = (created = "2026-01-01T00:00:00Z") =>
    find(
      buildColumns(
        context({
          checkpoints: [CHECKPOINT],
          customFields: [customField("clicks", { due_checkpoint_id: "d0", created_at: created })],
        }),
      ),
      "custom:clicks",
    );

  it("is tinted once its day has come", () => {
    expect(column().view(release("1", { release_date: "2026-05-01" })).tone).toBe("due");
  });

  it("is plain before that, and for dates before the field existed", () => {
    expect(column().view(release("1", { release_date: "2026-07-01" })).tone).toBe("later");
    const old = column("2026-05-15T00:00:00Z").view(release("1", { release_date: "2026-05-01" }));
    expect(old.tone).toBe("later");
  });
});

describe("choosing columns", () => {
  const list = buildColumns(context({ measures: MEASURES }));

  it("keeps only differences from the default, so a new column still shows up", () => {
    const unit = find(list, "unit");
    const journal = find(list, "journal");
    let choice = toggleColumn(unit, { hidden: [], shown: [] }, false);
    expect(choice).toEqual({ hidden: ["unit"], shown: [] });
    choice = toggleColumn(journal, choice, true);
    expect(choice).toEqual({ hidden: ["unit"], shown: ["journal"] });
    expect(isVisible(unit, choice)).toBe(false);
    expect(isVisible(journal, choice)).toBe(true);
    choice = toggleColumn(unit, choice, true);
    expect(choice).toEqual({ hidden: [], shown: ["journal"] });
  });

  it("never hides what is locked", () => {
    expect(isVisible(find(list, "title"), { hidden: ["title"], shown: [] })).toBe(true);
  });
});

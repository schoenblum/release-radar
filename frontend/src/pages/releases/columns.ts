import type { TFunction } from "i18next";

import type {
  Author,
  Checkpoint,
  CoreField,
  CustomField,
  CustomValue,
  Measure,
  Reading,
  Release,
  ResearchField,
  Unit,
  VocabularyItem,
  Writer,
} from "../../api/types";
import { translate } from "../../i18n";
import { formatNumber, isNotApplicable, normaliseDate, parseBoolean } from "./parse";

/** How the grid edits a column. "none" is edited in the drawer, as it needs more room. */
export type EditorKind =
  | "text"
  | "number"
  | "date"
  | "select"
  | "boolean"
  | "researcher"
  | "none";

export interface Option {
  value: string;
  label: string;
  /** Other words that mean this option, for paste. */
  words?: string[];
}

export type ReadingBody = { value: unknown } | { state: "not_applicable" | "missing" };
export type CustomBody = { value: unknown } | { state: "not_applicable" | "missing" };

/** One save, of whichever kind. */
export type Commit =
  | { kind: "field"; field: string; value: unknown }
  | { kind: "reading"; readingId: string; body: ReadingBody }
  | { kind: "custom"; key: string; body: CustomBody };

export type Tone = "due" | "na" | "later" | "muted" | "plain";

export interface CellView {
  text: string;
  tone: Tone;
  /** Shown on hover. */
  hint?: string;
  /** A boolean column shows a box instead of text. */
  checked?: boolean;
}

export type Parsed = { ok: true; commit: Commit } | { ok: false; code: string };

export type ColumnGroup = "release" | "paper" | "numbers" | "custom" | "colleagues";

export interface GridColumn {
  id: string;
  label: string;
  group: ColumnGroup;
  width: number;
  frozen: boolean;
  /** Shown unless someone has hidden it. */
  byDefault: boolean;
  /** Always shown: the grid makes no sense without it. */
  locked: boolean;
  alignRight: boolean;
  editor: EditorKind;
  options: Option[];
  view: (release: Release) => CellView;
  /** What an editor starts with, and what a copy gives. */
  editText: (release: Release) => string;
  isEditable: (release: Release) => boolean;
  parse: (text: string, release: Release) => Parsed;
  /** The save that would put this cell back as it is now, for undo. */
  snapshot: (release: Release) => Commit | null;
}

export interface GridContext {
  t: TFunction;
  language: "en" | "ja";
  today: string;
  canEdit: boolean;
  userId: string | null;
  coreFields: CoreField[];
  checkpoints: Checkpoint[];
  measures: Measure[];
  customFields: CustomField[];
  units: Unit[];
  fields: ResearchField[];
  writers: Writer[];
  vocabularyItems: Record<string, VocabularyItem[]>;
}

// R7.5.2.
const DEFAULT_CORE = new Set([
  "code",
  "title",
  "release_date",
  "researcher",
  "unit",
  "doi",
  "ea_top_page",
]);
const PAPER_FIELDS = new Set(["doi", "journal", "paper_title", "publication_date", "authors"]);
const LOCKED = new Set(["code", "title"]);
const FROZEN = new Set(["code", "title"]);
const DEFAULT_WIDTH = 170;
const WIDTHS: Record<string, number> = {
  code: 104,
  title: 320,
  title_ja: 280,
  release_date: 116,
  doi: 64,
  publication_date: 116,
  embargoed: 90,
  release_time_et: 96,
  ea_top_page: 90,
  ea_top_position: 90,
  paper_title: 280,
  notes: 240,
};
const MEASURE_WIDTH = 132;

function named(language: "en" | "ja", en: string, ja: string | null | undefined): string {
  return (language === "ja" && ja) || en;
}

function coreLabel(context: GridContext, config: CoreField): string {
  const custom = context.language === "ja" ? config.label_ja : config.label_en;
  return custom || translate(context.t, `release_fields.${config.key}`);
}

const plain = (text: string, tone: Tone = "plain"): CellView => ({ text, tone });

function authorName(author: Author): string {
  return author.name ?? [author.given, author.family].filter(Boolean).join(" ");
}

interface CoreSpec {
  field: string;
  editor: EditorKind;
  options?: Option[];
  view?: (release: Release) => CellView;
  editText?: (release: Release) => string;
  clean?: (text: string) => unknown;
  /** Only ever shown here, and changed elsewhere. */
  readOnly?: boolean;
}

function matchOption(options: Option[], text: string): string | null {
  const wanted = text.normalize("NFKC").trim().toLowerCase();
  const found = options.find((option) =>
    [option.value, option.label, ...(option.words ?? [])].some(
      (word) => word.normalize("NFKC").trim().toLowerCase() === wanted,
    ),
  );
  return found?.value ?? null;
}

function viewOption(options: Option[], id: string | null | undefined): CellView {
  return plain(options.find((option) => option.value === id)?.label ?? "");
}

function coreSpec(context: GridContext, key: string): CoreSpec | null {
  const { language, t } = context;
  const units: Option[] = context.units
    .filter((unit) => unit.is_active)
    .map((unit) => ({
      value: unit.id,
      label: named(language, unit.name_en, unit.name_ja),
      words: [unit.key, unit.name_en, unit.name_ja ?? "", unit.short_label ?? "", ...unit.aliases],
    }));
  const fields: Option[] = context.fields
    .filter((field) => field.is_active)
    .map((field) => ({
      value: field.id,
      label: named(language, field.name_en, field.name_ja),
      words: [field.name_en, field.name_ja ?? ""],
    }));
  const writers: Option[] = context.writers
    .filter((writer) => writer.is_active)
    .map((writer) => ({
      value: writer.id,
      label: named(language, writer.display_name_en, writer.display_name_ja),
      words: [writer.display_name_en, writer.display_name_ja ?? "", writer.full_name ?? ""],
    }));
  // A retired entry still shows on the releases that have it.
  const allUnits: Option[] = context.units.map((unit) => ({
    value: unit.id,
    label: named(language, unit.name_en, unit.name_ja),
  }));
  const allFields: Option[] = context.fields.map((field) => ({
    value: field.id,
    label: named(language, field.name_en, field.name_ja),
  }));
  const allWriters: Option[] = context.writers.map((writer) => ({
    value: writer.id,
    label: named(language, writer.display_name_en, writer.display_name_ja),
  }));

  switch (key) {
    case "code":
      return {
        field: "code",
        editor: "none",
        readOnly: true,
        view: (release) =>
          release.code
            ? plain(release.code)
            : { text: "—", tone: "muted", hint: t("data.code_hint") },
      };
    case "title":
      return {
        field: key,
        editor: "text",
        // Created from a DOI alone, it has no title yet. What the paper is called will do.
        view: (release) =>
          release.title
            ? plain(release.title)
            : { text: release.paper_title ?? release.doi ?? "", tone: "muted" },
      };
    case "title_ja":
    case "also_featured":
    case "journal":
    case "paper_title":
    case "ea_url":
    case "website_url":
      return { field: key, editor: "text" };
    case "doi":
      return {
        field: "doi",
        editor: "text",
        view: (release) =>
          release.doi ? { text: "✓", tone: "plain", hint: release.doi } : plain(""),
      };
    case "writer":
      return {
        field: "writer_id",
        editor: "select",
        options: writers,
        view: (release) => viewOption(allWriters, release.writer_id),
      };
    case "researcher":
      return {
        field: "researcher_id",
        editor: "researcher",
        view: (release) => plain(release.researcher_name ?? ""),
        editText: (release) => release.researcher_name ?? "",
      };
    case "unit":
      return {
        field: "unit_id",
        editor: "select",
        options: units,
        view: (release) => viewOption(allUnits, release.unit_id),
      };
    case "field":
      return {
        field: "field_id",
        editor: "select",
        options: fields,
        view: (release) => viewOption(allFields, release.field_id),
      };
    case "publication_date":
    case "release_date":
      return { field: key, editor: "date", clean: normaliseDate };
    case "release_time_et":
      return {
        field: key,
        editor: "text",
        view: (release) => plain(release.release_time_et?.slice(0, 5) ?? ""),
        editText: (release) => release.release_time_et?.slice(0, 5) ?? "",
      };
    case "embargoed":
      return { field: key, editor: "boolean" };
    case "ea_top_page":
      return { field: key, editor: "boolean" };
    case "ea_top_position":
      return { field: key, editor: "number" };
    case "authors":
      return {
        field: key,
        editor: "none",
        view: (release) => plain(release.authors.map(authorName).join(", ")),
        editText: (release) => release.authors.map(authorName).join(", "),
      };
    case "notes":
      return {
        field: key,
        editor: "none",
        view: (release) => plain((release.notes ?? "").split("\n")[0]),
        editText: (release) => release.notes ?? "",
      };
    default:
      return null;
  }
}

function coreColumn(context: GridContext, config: CoreField): GridColumn | null {
  const spec = coreSpec(context, config.key);
  if (!spec) return null;
  const { field, editor, options = [], readOnly = false } = spec;
  const raw = (release: Release): unknown => (release as unknown as Record<string, unknown>)[field];
  const isBoolean = editor === "boolean";
  return {
    id: config.key,
    label: coreLabel(context, config),
    group: PAPER_FIELDS.has(config.key) ? "paper" : "release",
    width: WIDTHS[config.key] ?? DEFAULT_WIDTH,
    frozen: FROZEN.has(config.key),
    byDefault: DEFAULT_CORE.has(config.key),
    locked: LOCKED.has(config.key),
    alignRight: false,
    editor,
    options,
    view:
      spec.view ??
      ((release) =>
        isBoolean
          ? { text: "", tone: "plain", checked: Boolean(raw(release)) }
          : plain(raw(release) == null ? "" : String(raw(release)))),
    editText:
      spec.editText ??
      ((release) => {
        const value = raw(release);
        if (isBoolean) return value ? "✓" : "";
        if (options.length > 0) return options.find((o) => o.value === value)?.label ?? "";
        return value == null ? "" : String(value);
      }),
    isEditable: () => context.canEdit && !readOnly,
    parse: (text) => {
      if (readOnly || editor === "none") return { ok: false, code: "field_not_editable" };
      if (editor === "researcher") {
        // A name alone cannot say which record is meant (R6.3.1), so only clearing works here.
        return text.trim() === ""
          ? { ok: true, commit: { kind: "field", field, value: null } }
          : { ok: false, code: "researcher_needs_choosing" };
      }
      if (isBoolean) {
        const value = parseBoolean(text);
        return value === null
          ? { ok: false, code: "field_invalid" }
          : { ok: true, commit: { kind: "field", field, value } };
      }
      if (options.length > 0 || editor === "select") {
        if (text.trim() === "") return { ok: true, commit: { kind: "field", field, value: null } };
        const value = matchOption(options, text);
        return value === null
          ? { ok: false, code: "field_invalid" }
          : { ok: true, commit: { kind: "field", field, value } };
      }
      return {
        ok: true,
        commit: { kind: "field", field, value: spec.clean ? spec.clean(text) : text },
      };
    },
    snapshot: (release) =>
      readOnly || editor === "none" ? null : { kind: "field", field, value: raw(release) },
  };
}

function findReading(release: Release, measureId: string): Reading | undefined {
  return release.readings.find((reading) => reading.measure_id === measureId);
}

export function readingSnapshot(reading: Reading): ReadingBody {
  if (reading.state === "value") return { value: reading.value };
  // A person's N/A comes back as such. A rule's goes back to the rules, which set it again.
  if (reading.state === "not_applicable" && reading.source === "manual") {
    return { state: "not_applicable" };
  }
  return { state: "missing" };
}

function measureColumn(context: GridContext, measure: Measure): GridColumn {
  const { t } = context;
  // Entered by hand here. An automatic value can be overridden in the drawer (P4).
  const isManual = measure.source === "manual";
  const dueHint = (reading: Reading): string | undefined =>
    reading.due_date ? t("data.due_on", { date: reading.due_date }) : undefined;
  return {
    id: `measure:${measure.key}`,
    label: named(context.language, measure.label_en, measure.label_ja),
    group: "numbers",
    width: MEASURE_WIDTH,
    frozen: false,
    byDefault: true,
    locked: false,
    alignRight: true,
    editor: isManual ? "number" : "none",
    options: [],
    view: (release) => {
      const reading = findReading(release, measure.id);
      if (!reading) return { text: "", tone: "muted" };
      if (reading.display_state === "value") return plain(formatNumber(reading.value ?? 0));
      if (reading.display_state === "not_applicable") {
        return { text: t("data.not_applicable"), tone: "na" };
      }
      if (reading.display_state === "not_yet_due") {
        return { text: "", tone: "later", hint: dueHint(reading) };
      }
      // Due and empty. Neutral on purpose: nothing here is late (P5).
      return { text: "", tone: isManual ? "due" : "muted", hint: dueHint(reading) };
    },
    editText: (release) => {
      const reading = findReading(release, measure.id);
      if (reading?.state === "value") return String(reading.value);
      return reading?.state === "not_applicable" ? "N/A" : "";
    },
    isEditable: (release) => context.canEdit && isManual && !!findReading(release, measure.id),
    parse: (text, release) => {
      const reading = findReading(release, measure.id);
      if (!reading || !isManual) return { ok: false, code: "field_not_editable" };
      const commit = (body: ReadingBody): Parsed => ({
        ok: true,
        commit: { kind: "reading", readingId: reading.id, body },
      });
      if (text.trim() === "") return commit({ state: "missing" });
      if (isNotApplicable(text)) return commit({ state: "not_applicable" });
      return commit({ value: text });
    },
    snapshot: (release) => {
      const reading = findReading(release, measure.id);
      return reading ? { kind: "reading", readingId: reading.id, body: readingSnapshot(reading) } : null;
    },
  };
}

export function customOptions(context: GridContext, field: CustomField): Option[] {
  if (field.vocabulary_id) {
    return (context.vocabularyItems[field.vocabulary_id] ?? []).map((item) => ({
      value: item.key,
      label: named(context.language, item.label_en, item.label_ja),
      words: [item.label_en, item.label_ja ?? "", ...item.aliases],
    }));
  }
  return field.options.map((option) => ({
    value: option.key,
    label: named(context.language, option.label_en, option.label_ja),
    words: [option.label_en, option.label_ja ?? ""],
  }));
}

export function customValueText(
  value: CustomValue | undefined,
  options: Option[],
  field: CustomField,
): string {
  if (!value || value.state !== "value") return "";
  const raw = value.value;
  if (field.field_type === "boolean") return raw ? "✓" : "";
  if (Array.isArray(raw)) {
    return raw.map((key) => options.find((o) => o.value === key)?.label ?? String(key)).join(", ");
  }
  if (field.field_type === "single_select") {
    return options.find((o) => o.value === raw)?.label ?? String(raw);
  }
  if (typeof raw === "number") return formatNumber(raw);
  return raw == null ? "" : String(raw);
}

const CUSTOM_EDITORS: Record<CustomField["field_type"], EditorKind> = {
  integer: "number",
  number: "number",
  text: "text",
  url: "text",
  date: "date",
  boolean: "boolean",
  single_select: "select",
  long_text: "none",
  multi_select: "none",
};

export function customColumnId(field: CustomField): string {
  return `custom:${field.key}`;
}

function customColumn(context: GridContext, field: CustomField): GridColumn {
  const { t } = context;
  const editor = CUSTOM_EDITORS[field.field_type];
  const options = customOptions(context, field);
  const isMine = field.scope === "personal" && field.owner_id === context.userId;
  const isColleagues = field.scope === "personal" && !isMine;
  const label = named(context.language, field.label_en, field.label_ja);
  const checkpoint = context.checkpoints.find((row) => row.id === field.due_checkpoint_id);
  const createdOn = field.created_at.slice(0, 10);
  const canEdit =
    context.canEdit && field.is_active && (field.scope === "institution" || isMine);

  const dueDate = (release: Release): string | null => {
    if (!checkpoint || !release.release_date) return null;
    const date = new Date(`${release.release_date}T00:00:00Z`);
    date.setUTCDate(date.getUTCDate() + checkpoint.offset_days);
    return date.toISOString().slice(0, 10);
  };

  return {
    id: customColumnId(field),
    label: isColleagues ? t("data.owned_by", { label, owner: field.owner_name ?? "" }) : label,
    group: isColleagues ? "colleagues" : "custom",
    width: field.field_type === "boolean" ? 90 : DEFAULT_WIDTH,
    frozen: false,
    byDefault: isMine || (field.scope === "institution" && field.required),
    locked: false,
    alignRight: editor === "number",
    editor: canEdit ? editor : "none",
    options,
    view: (release) => {
      const value = release.custom_values[field.key];
      if (value?.state === "not_applicable") return { text: t("data.not_applicable"), tone: "na" };
      if (field.field_type === "boolean") {
        return {
          text: "",
          tone: "plain",
          checked: value?.state === "value" && Boolean(value.value),
        };
      }
      const text = customValueText(value, options, field);
      if (text) return plain(text);
      const due = dueDate(release);
      if (!due) return { text: "", tone: "plain" };
      const hint = t("data.due_on", { date: due });
      // A field does not ask for dates before it existed, as the due list does not either.
      if (due > context.today || due < createdOn) return { text: "", tone: "later", hint };
      return { text: "", tone: canEdit ? "due" : "muted", hint };
    },
    editText: (release) => {
      const value = release.custom_values[field.key];
      if (value?.state === "not_applicable") return "N/A";
      if (value?.state !== "value") return "";
      if (field.field_type === "single_select") {
        return options.find((o) => o.value === value.value)?.label ?? String(value.value);
      }
      return customValueText(value, options, field);
    },
    isEditable: () => canEdit && editor !== "none",
    parse: (text) => {
      if (!canEdit || editor === "none") return { ok: false, code: "field_not_editable" };
      const commit = (body: CustomBody): Parsed => ({
        ok: true,
        commit: { kind: "custom", key: field.key, body },
      });
      if (text.trim() === "") return commit({ state: "missing" });
      if (isNotApplicable(text)) return commit({ state: "not_applicable" });
      if (editor === "boolean") {
        const value = parseBoolean(text);
        return value === null ? { ok: false, code: "field_invalid" } : commit({ value });
      }
      if (editor === "select") {
        const value = matchOption(options, text);
        return value === null ? { ok: false, code: "field_invalid" } : commit({ value });
      }
      if (editor === "date") return commit({ value: normaliseDate(text) });
      return commit({ value: text });
    },
    snapshot: (release) => {
      if (!canEdit || editor === "none") return null;
      const value = release.custom_values[field.key];
      const body: CustomBody =
        value?.state === "value"
          ? { value: value.value }
          : value?.state === "not_applicable"
            ? { state: "not_applicable" }
            : { state: "missing" };
      return { kind: "custom", key: field.key, body };
    },
  };
}

/**
 * All the columns anyone could show, in order (R7.5.2): the code, title and date first, the
 * built-in fields up to the DOI as Settings orders them, the numbers, the remaining built-in
 * fields, then custom fields, the person's own first. Hidden built-in fields are left out.
 */
export function buildColumns(context: GridContext): GridColumn[] {
  const core = [...context.coreFields]
    .filter((config) => !config.hidden)
    .sort((a, b) => a.position - b.position);
  const doiAt = core.findIndex((config) => config.key === "doi");
  const leading = ["code", "title", "release_date"];
  const first = leading
    .map((key) => core.find((config) => config.key === key))
    .filter((config): config is CoreField => !!config);
  const rest = core.filter((config) => !leading.includes(config.key));
  const cut = doiAt === -1 ? rest.length : rest.findIndex((config) => config.key === "doi") + 1;

  const measures = [...context.measures]
    .filter((measure) => measure.is_active)
    .sort((a, b) => a.position - b.position);
  const custom = [...context.customFields].filter((field) => field.is_active);
  const rank = (field: CustomField): number =>
    field.scope === "institution" ? 0 : field.owner_id === context.userId ? 1 : 2;
  custom.sort((a, b) => rank(a) - rank(b) || a.position - b.position);

  return [
    ...[...first, ...rest.slice(0, cut)].map((config) => coreColumn(context, config)),
    ...measures.map((measure) => measureColumn(context, measure)),
    ...rest.slice(cut).map((config) => coreColumn(context, config)),
    ...custom.map((field) => customColumn(context, field)),
  ].filter((column): column is GridColumn => column !== null);
}

export interface ColumnChoice {
  hidden: string[];
  shown: string[];
}

export function isVisible(column: GridColumn, choice: ColumnChoice): boolean {
  if (column.locked) return true;
  if (choice.hidden.includes(column.id)) return false;
  return column.byDefault || choice.shown.includes(column.id);
}

/** Only differences from the default are kept, so a column added later still shows up. */
export function toggleColumn(
  column: GridColumn,
  choice: ColumnChoice,
  visible: boolean,
): ColumnChoice {
  const hidden = choice.hidden.filter((id) => id !== column.id);
  const shown = choice.shown.filter((id) => id !== column.id);
  if (visible && !column.byDefault) shown.push(column.id);
  if (!visible && column.byDefault) hidden.push(column.id);
  return { hidden, shown };
}

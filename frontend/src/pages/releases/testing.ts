// For tests only. Synthetic data.
import i18n from "../../i18n";
import type {
  CoreField,
  CustomField,
  Measure,
  Reading,
  Release,
  Unit,
} from "../../api/types";
import type { GridContext } from "./columns";

const CORE_KEYS = [
  "code",
  "title",
  "title_ja",
  "writer",
  "researcher",
  "also_featured",
  "unit",
  "field",
  "doi",
  "journal",
  "paper_title",
  "publication_date",
  "authors",
  "embargoed",
  "release_date",
  "release_time_et",
  "ea_url",
  "website_url",
  "ea_top_page",
  "ea_top_position",
  "notes",
];

export function coreFields(changes: Partial<Record<string, Partial<CoreField>>> = {}): CoreField[] {
  return CORE_KEYS.map((key, position) => ({
    id: `core-${key}`,
    key,
    label_en: null,
    label_ja: null,
    hidden: key === "title_ja",
    required: false,
    position,
    can_hide: true,
    can_require: true,
    field_versions: {},
    ...changes[key],
  }));
}

export function measure(key: string, changes: Partial<Measure> = {}): Measure {
  return {
    id: `measure-${key}`,
    key,
    metric: key.split(".")[0],
    checkpoint_id: null,
    source: "manual",
    applicability: "always",
    unit: "views",
    label_en: key,
    label_ja: `${key}（日本語）`,
    position: 0,
    is_active: true,
    collected_from: null,
    field_versions: {},
    ...changes,
  };
}

export function reading(key: string, changes: Partial<Reading> = {}): Reading {
  return {
    id: `reading-${key}`,
    measure_id: `measure-${key}`,
    measure_key: key,
    value: null,
    state: "missing",
    display_state: "missing",
    source: "auto",
    due_date: "2026-05-29",
    remind_on: "2026-05-29",
    note: null,
    version: 1,
    entered_at: null,
    ...changes,
  };
}

export function customField(key: string, changes: Partial<CustomField> = {}): CustomField {
  return {
    id: `field-${key}`,
    key,
    label_en: key,
    label_ja: null,
    help_en: null,
    help_ja: null,
    field_type: "integer",
    options: [],
    vocabulary_id: null,
    scope: "personal",
    owner_id: "me",
    owner_name: "Me",
    owner_active: true,
    required: false,
    position: 0,
    is_active: true,
    due_checkpoint_id: null,
    score_eligible: false,
    created_at: "2026-01-01T00:00:00Z",
    field_versions: {},
    ...changes,
  };
}

export const UNIT: Unit = {
  id: "unit-1",
  key: "SCI",
  name_en: "School of Science",
  name_ja: "理学研究科",
  short_label: "Science",
  unit_type: "school",
  aliases: ["Science School"],
  default_field_id: null,
  is_active: true,
  field_versions: {},
};

export function release(id: string, changes: Partial<Release> = {}): Release {
  return {
    id,
    code: `AY2026-${id}`,
    title: `Release ${id}`,
    title_ja: null,
    writer_id: null,
    researcher_id: null,
    researcher_name: null,
    also_featured: null,
    unit_id: null,
    field_id: null,
    doi: null,
    journal: null,
    paper_title: null,
    publication_date: null,
    authors: [],
    embargoed: false,
    release_date: "2026-05-01",
    academic_year: 2026,
    release_time_et: null,
    ea_url: null,
    website_url: null,
    ea_top_page: false,
    ea_top_position: null,
    notes: null,
    custom_values: {},
    field_versions: {},
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
    readings: [],
    warnings: [],
    missing_required: [],
    ...changes,
  };
}

export function context(changes: Partial<GridContext> = {}): GridContext {
  return {
    t: i18n.t,
    language: "en",
    today: "2026-06-01",
    canEdit: true,
    userId: "me",
    coreFields: coreFields(),
    checkpoints: [],
    measures: [],
    customFields: [],
    units: [UNIT],
    fields: [],
    writers: [],
    vocabularyItems: {},
    ...changes,
  };
}

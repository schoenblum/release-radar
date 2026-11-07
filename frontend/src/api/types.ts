// Mirrors the backend schemas in app/schemas. Change both together.
import type { Language } from "../i18n";

export type UserRole = "admin" | "editor" | "viewer";
export type LandingView = "mine" | "all";
export type FieldVersions = Record<string, number>;

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  language: Language | null;
  is_active: boolean;
  force_password_change: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface UserPreferences {
  /** Differences from the default columns, so a column added later still shows up. */
  data_columns: { hidden: string[]; shown: string[] };
}

/** The signed-in person, with where they land after signing in. */
export interface CurrentUser extends User {
  landing: LandingView;
  preferences: UserPreferences;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: CurrentUser;
}

export interface ForgotPasswordResult {
  email_enabled: boolean;
}

export interface Brand {
  theme: string;
  institution_name_en: string;
  institution_name_ja: string | null;
  timezone: string;
  logo: { url: string; alt_en: string | null; alt_ja: string | null } | null;
}

export interface Health {
  status: string;
  version: string;
}

export interface FieldSaved {
  field: string;
  value: unknown;
  version: number;
}

export interface UserCreated {
  user: User;
  email_sent: boolean;
  initial_password: string | null;
}

export interface PasswordReset {
  email_sent: boolean;
  initial_password: string | null;
}

export interface Institution {
  id: string;
  name_en: string;
  name_ja: string | null;
  timezone: string;
  ay_start_month: number;
  website_domain: string | null;
  release_code_pattern: string;
  landing_pages: Record<UserRole, LandingView>;
  contact_email: string | null;
  field_versions: FieldVersions;
}

export interface ResearchField {
  id: string;
  name_en: string;
  name_ja: string | null;
  scope_note: string | null;
  is_active: boolean;
  field_versions: FieldVersions;
}

export interface Unit {
  id: string;
  key: string;
  name_en: string;
  name_ja: string | null;
  short_label: string | null;
  unit_type: string | null;
  aliases: string[];
  default_field_id: string | null;
  is_active: boolean;
  field_versions: FieldVersions;
}

export interface Writer {
  id: string;
  display_name_en: string;
  display_name_ja: string | null;
  full_name: string | null;
  user_id: string | null;
  is_active: boolean;
  field_versions: FieldVersions;
}

export interface Vocabulary {
  id: string;
  key: string;
  name_en: string;
  name_ja: string | null;
  is_active: boolean;
  field_versions: FieldVersions;
}

export interface VocabularyItem {
  id: string;
  vocabulary_id: string;
  key: string;
  label_en: string;
  label_ja: string | null;
  aliases: string[];
  position: number;
  is_active: boolean;
  field_versions: FieldVersions;
}

export interface ImportProblem {
  row: number;
  key: string;
  /** Null when the whole row could not be used, rather than one cell. */
  column: string | null;
  value: string;
  code: string;
  /** What to use instead, where that is a short list. */
  allowed: string[];
}

export interface ImportReport {
  created: number;
  updated: number;
  unchanged: number;
  errors: ImportProblem[];
  dry_run: boolean;
}

export interface Checkpoint {
  id: string;
  key: string;
  label_en: string;
  label_ja: string | null;
  /** Negative falls before the release date. */
  offset_days: number;
  /** When the reminder goes out: 0 at the start of the due day, 1 the day before. */
  remind_days_before: 0 | 1;
  field_versions: FieldVersions;
}

export interface Measure {
  id: string;
  key: string;
  metric: string;
  checkpoint_id: string | null;
  source: string;
  applicability: string;
  unit: string;
  label_en: string;
  label_ja: string | null;
  position: number;
  is_active: boolean;
  collected_from: string | null;
  field_versions: FieldVersions;
}

export interface CoreField {
  id: string;
  key: string;
  label_en: string | null;
  label_ja: string | null;
  hidden: boolean;
  required: boolean;
  position: number;
  can_hide: boolean;
  can_require: boolean;
  field_versions: FieldVersions;
}

export type CustomFieldType =
  | "integer"
  | "number"
  | "text"
  | "long_text"
  | "date"
  | "boolean"
  | "single_select"
  | "multi_select"
  | "url";

export interface CustomFieldOption {
  key: string;
  label_en: string;
  label_ja: string | null;
}

export interface CustomField {
  id: string;
  key: string;
  label_en: string;
  label_ja: string | null;
  help_en: string | null;
  help_ja: string | null;
  field_type: CustomFieldType;
  options: CustomFieldOption[];
  vocabulary_id: string | null;
  scope: "institution" | "personal";
  owner_id: string | null;
  owner_name: string | null;
  owner_active: boolean | null;
  required: boolean;
  position: number;
  is_active: boolean;
  due_checkpoint_id: string | null;
  score_eligible: boolean;
  created_at: string;
  field_versions: FieldVersions;
}

export interface Researcher {
  id: string;
  merged_into_id: string | null;
  name: string;
  given_name: string | null;
  family_name: string | null;
  name_ja: string | null;
  current_unit_id: string | null;
  gender: string;
  researchmap_id: string | null;
  orcid: string | null;
  status: string;
  notes: string | null;
  created_at: string;
  field_versions: FieldVersions;
  release_count: number;
  /** Other records with the same name, which are different people until merged. */
  same_name_count: number;
  merged_count: number;
}

export interface ResearcherPage {
  items: Researcher[];
  total: number;
}

export interface ResearcherRelease {
  id: string;
  code: string | null;
  title: string | null;
  paper_title: string | null;
  release_date: string | null;
}

export interface MergedRecord {
  id: string;
  name: string;
  updated_at: string;
  release_count: number;
}

export interface ResearcherDetail extends Researcher {
  releases: ResearcherRelease[];
  merged_records: MergedRecord[];
}

export interface SplitResult {
  source: Researcher;
  target: Researcher;
  created: boolean;
}

export interface UnmergeResult {
  restored: Researcher;
  survivor: Researcher;
}

export type StoredReadingState = "value" | "not_applicable" | "missing";

export interface Reading {
  id: string;
  measure_id: string;
  measure_key: string;
  value: number | null;
  state: StoredReadingState;
  display_state: StoredReadingState | "not_yet_due";
  source: "manual" | "auto";
  due_date: string | null;
  remind_on: string | null;
  note: string | null;
  version: number;
  entered_at: string | null;
}

export interface Author {
  given: string | null;
  family: string | null;
  name: string | null;
  orcid: string | null;
}

export type CustomValue = { state: "value"; value: unknown } | { state: "not_applicable" };

export interface Release {
  id: string;
  /** Assigned by the system when a release date is first entered, then never changed. */
  code: string | null;
  title: string | null;
  title_ja: string | null;
  writer_id: string | null;
  researcher_id: string | null;
  researcher_name: string | null;
  also_featured: string | null;
  unit_id: string | null;
  field_id: string | null;
  doi: string | null;
  journal: string | null;
  paper_title: string | null;
  publication_date: string | null;
  authors: Author[];
  embargoed: boolean;
  release_date: string | null;
  /** From the date, never from the code. */
  academic_year: number | null;
  release_time_et: string | null;
  ea_url: string | null;
  website_url: string | null;
  ea_top_page: boolean;
  ea_top_position: number | null;
  notes: string | null;
  custom_values: Record<string, CustomValue>;
  field_versions: FieldVersions;
  created_at: string;
  updated_at: string;
  readings: Reading[];
  warnings: ("ea_url_unusual" | "website_off_domain")[];
  missing_required: string[];
}

export interface ReleasePage {
  items: Release[];
  total: number;
  has_writer_entry: boolean;
}

export type CrossrefStatus = "found" | "not_found" | "unavailable";

export interface ReleaseCreated extends Release {
  crossref: CrossrefStatus | null;
}

export interface ReleaseSaved extends FieldSaved {
  release: Release;
}

export interface DoiLookupResult {
  doi: string;
  status: CrossrefStatus;
  journal: string | null;
  paper_title: string | null;
  publication_date: string | null;
  authors: Author[];
}

/** Something this person is asked for. There is no notion of late. */
export interface DueItem {
  kind: "reading" | "custom";
  release_id: string;
  release_code: string | null;
  release_title: string | null;
  due_date: string;
  /** False means it is coming up in the next few days. */
  due_now: boolean;
  label_en: string;
  label_ja: string | null;
  version: number;
  reading_id: string | null;
  measure_key: string | null;
  measure_unit: string | null;
  field_key: string | null;
  field_type: CustomFieldType | null;
}

export interface HistoryEntry {
  at: string;
  action: "create" | "update" | "delete";
  entity: "release" | "reading";
  measure_key: string | null;
  field: string | null;
  old_value: unknown;
  new_value: unknown;
  old_label: string | null;
  new_label: string | null;
  user_id: string | null;
  user_name: string | null;
  user_active: boolean | null;
}

export interface JobRun {
  job_key: string;
  slot: string;
  status: "running" | "succeeded" | "skipped" | "failed";
  detail: string | null;
  worker: string | null;
  started_at: string;
  finished_at: string | null;
}

export interface BackupStatus {
  configured: boolean;
  retention_days: number;
  latest: { filename: string; size_bytes: number; created_at: string } | null;
  last_run: JobRun | null;
}

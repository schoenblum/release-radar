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
  /** What new releases start as (R6.4.1); null: they start without a type. */
  default_release_type_id: string | null;
  field_versions: FieldVersions;
}

/** What kind of release it is, after EurekAlert's categories (R6.4.1). */
export interface ReleaseType {
  id: string;
  key: string;
  name_en: string;
  name_ja: string | null;
  aliases: string[];
  position: number;
  is_active: boolean;
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
  /** The researcher's: F, M or other; null when not recorded or there is no researcher. */
  researcher_gender: "F" | "M" | "other" | null;
  also_featured: string | null;
  unit_id: string | null;
  field_id: string | null;
  release_type_id: string | null;
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
  /** How many match the filters, of how many in the view (Mine or All) as a whole. */
  total: number;
  view_total: number;
  has_writer_entry: boolean;
  /** Every academic year with releases, newest first. */
  academic_years: number[];
}

/** What the Data page can narrow a view to (R7.6.1). The names are the API's. */
export interface ReleaseFilters {
  academic_year?: number;
  field_id?: string;
  unit_id?: string;
  researcher_id?: string;
  writer_id?: string;
  /** "none": releases without a type. */
  release_type_id?: string;
  q?: string;
}

export interface ReleaseExportRequest {
  format: "xlsx" | "csv";
  language: "en" | "ja";
  /** Absent: everything. */
  filters?: ReleaseFilters & { view: LandingView };
  order: string[];
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

/** What a test of the Google Analytics connection found (R8.1.1). */
export interface Ga4TestResult {
  ok: boolean;
  /** connected, connected_no_views, or why it failed: api_disabled, no_access, … */
  code: string;
  detail: string | null;
  views?: number;
  date: string;
  host: string | null;
}

export interface Ga4WaitingRelease {
  release_id: string;
  code: string | null;
  title: string | null;
  website_url: string;
  release_date: string;
}

/** Settings → Integrations → Google Analytics. The key itself never comes back. */
export interface Ga4Status {
  configured: boolean;
  /** False for a key stored on another install, under another encryption key. */
  readable: boolean;
  client_email: string | null;
  project_id: string | null;
  property_id: string | null;
  field_versions: Record<string, number>;
  domain: string | null;
  first_fetch_at: string | null;
  last_test_at: string | null;
  last_test: Ga4TestResult | null;
  last_run: JobRun | null;
  running: boolean;
  fetched: number;
  waiting: Ga4WaitingRelease[];
  not_yet_due: number;
}

/** The Writers page (R7.7.1): releases per writer, counts only. */
export interface WriterCountRow {
  /** Null for releases that have no writer yet. */
  writer_id: string | null;
  name_en: string | null;
  name_ja: string | null;
  is_active: boolean;
  counts: number[];
  total: number;
}

export interface WriterCounts {
  /** Month by month for one academic year, or year by year for all of them. */
  period: "month" | "year";
  /** The year shown month by month; null for all years. */
  academic_year: number | null;
  /** Every year with releases, and the current one, newest first. */
  academic_years: number[];
  /** In order: YYYY-MM for months, YYYY for academic years. */
  columns: string[];
  rows: WriterCountRow[];
  totals: number[];
  total: number;
  /** Releases without a release date, which no column counts yet. */
  undated: number;
}

/** Import of the old workbook (step 1.8). A file travels base64-encoded in JSON. */
export interface UploadedFile {
  name: string;
  content: string;
}

/** Who owns each personal field seeded from the workbook; null: not imported. */
export interface PersonalFieldOwners {
  bitly: string | null;
  pitches: string | null;
  request_received: string | null;
}

export interface WorkbookImportResult {
  /** In the import history, where its report can be downloaded again. */
  run_id: string;
  committed: boolean;
  counts: Record<string, number>;
  /** The counts in order, labelled in the request's language. */
  summary: { label: string; count: number }[];
  /** Report entries by level: check, dash, info. */
  levels: Record<string, number>;
  markdown: string;
  csv: string;
  /** Without extension. */
  filename: string;
}

/** One check or import, as the import history lists it. */
export interface ImportRun {
  id: string;
  created_at: string;
  committed: boolean;
  file_names: string[];
  user_name: string | null;
  counts: Record<string, number>;
  levels: Record<string, number>;
}

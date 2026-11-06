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

/** The signed-in person, with where they land after signing in. */
export interface CurrentUser extends User {
  landing: LandingView;
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

export interface ImportReport {
  created: number;
  updated: number;
  unchanged: number;
  errors: { row: number; key: string; code: string }[];
  dry_run: boolean;
}

export interface Checkpoint {
  id: string;
  key: string;
  label_en: string;
  label_ja: string | null;
  offset_days: number;
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
  field_versions: FieldVersions;
}

export interface Researcher {
  id: string;
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
}

export interface ResearcherPage {
  items: Researcher[];
  total: number;
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

// Mirrors the backend schemas in app/schemas. Change both together.
import type { Language } from "../i18n";

export type UserRole = "admin" | "editor" | "viewer";

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

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface ForgotPasswordResult {
  email_enabled: boolean;
}

export interface Brand {
  theme: string;
  institution_name_en: string;
  institution_name_ja: string | null;
  logo: { url: string; alt_en: string | null; alt_ja: string | null } | null;
}

export interface Health {
  status: string;
  version: string;
}

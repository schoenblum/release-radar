import type { TFunction } from "i18next";

import i18n, { translate } from "../i18n";
import { ApiError } from "./client";

/** Turn an error code from the server into a friendly sentence. */
export function codeMessage(t: TFunction, code: string): string {
  const key = `errors.${code}`;
  return i18n.exists(key) ? translate(t, key) : t("errors.generic");
}

/** Turn any failure into a friendly sentence in the current language. */
export function errorMessage(t: TFunction, error: unknown): string {
  if (error instanceof ApiError) return codeMessage(t, error.code);
  if (error instanceof TypeError) return t("errors.network");
  return t("errors.generic");
}

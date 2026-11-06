import type { TFunction } from "i18next";

import i18n from "../i18n";
import { ApiError } from "./client";

/** Turn any failure into a friendly sentence in the current language. */
export function errorMessage(t: TFunction, error: unknown): string {
  if (error instanceof ApiError) {
    // The code comes from the server, so this key cannot be checked at compile time.
    const key = `errors.${error.code}`;
    return i18n.exists(key) ? (t as (key: string) => string)(key) : t("errors.generic");
  }
  if (error instanceof TypeError) return t("errors.network");
  return t("errors.generic");
}

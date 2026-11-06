import i18n, { type TFunction } from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en.json";
import ja from "./locales/ja.json";

export type Language = "en" | "ja";

const STORAGE_KEY = "rr_language";

function storedLanguage(): Language | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === "en" || value === "ja" ? value : null;
  } catch {
    return null;
  }
}

/** The saved choice, or else the browser's language (R5.4.2). */
export function detectLanguage(): Language {
  return storedLanguage() ?? (navigator.language.toLowerCase().startsWith("ja") ? "ja" : "en");
}

export function currentLanguage(): Language {
  return i18n.language === "ja" ? "ja" : "en";
}

export function applyLanguage(language: Language): void {
  void i18n.changeLanguage(language);
  document.documentElement.lang = language;
  try {
    localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // The choice then lasts only for this page load.
  }
}

const initialLanguage = detectLanguage();
document.documentElement.lang = initialLanguage;

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, ja: { translation: ja } },
  lng: initialLanguage,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

/** For keys that come from data, so they cannot be checked at compile time. */
export function translate(t: TFunction, key: string): string {
  return (t as (key: string) => string)(key);
}

export default i18n;

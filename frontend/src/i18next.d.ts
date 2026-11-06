import "i18next";

import type en from "./i18n/locales/en.json";

// A translation key that does not exist becomes a type error.
declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: "translation";
    resources: { translation: typeof en };
  }
}

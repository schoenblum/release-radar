import { useTranslation } from "react-i18next";

import { api } from "../api/client";
import { useAuth } from "../auth";
import { applyLanguage, currentLanguage } from "../i18n";

/** One click switches the language (R5.4.2). The label is in the language it switches to. */
export default function LanguageToggle() {
  const { t } = useTranslation();
  const { user, setUser } = useAuth();

  function toggle() {
    const next = currentLanguage() === "ja" ? "en" : "ja";
    applyLanguage(next);
    if (user) {
      // The screen has already switched, so a failed save only loses the preference.
      api
        .updateMe({ language: next })
        .then(setUser)
        .catch(() => undefined);
    }
  }

  return (
    <button
      type="button"
      className="btn-quiet"
      onClick={toggle}
      aria-label={t("language.switch_label")}
    >
      {t("language.switch_to")}
    </button>
  );
}

import { useTranslation } from "react-i18next";

import { errorMessage } from "../api/errors";

/** Shows a failure in the current language, including after the language is switched. */
export default function ErrorNotice({ error }: { error: unknown }) {
  const { t } = useTranslation();
  if (error === null) return null;
  return (
    <p role="alert" className="notice-error">
      {errorMessage(t, error)}
    </p>
  );
}

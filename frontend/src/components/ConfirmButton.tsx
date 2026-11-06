import { useState } from "react";
import { useTranslation } from "react-i18next";

/**
 * Asks once, in place, for actions with no simple undo. Reversible actions use an Undo
 * in the toast instead.
 */
export default function ConfirmButton({
  label,
  question,
  onConfirm,
}: {
  label: string;
  question: string;
  onConfirm: () => void;
}) {
  const { t } = useTranslation();
  const [asking, setAsking] = useState(false);
  if (!asking) {
    return (
      <button type="button" className="btn-small" onClick={() => setAsking(true)}>
        {label}
      </button>
    );
  }
  return (
    <span className="inline-flex flex-wrap items-center gap-5xs">
      <span className="text-sm">{question}</span>
      <button
        type="button"
        className="btn-small"
        onClick={() => {
          setAsking(false);
          onConfirm();
        }}
      >
        {t("common.yes")}
      </button>
      <button type="button" className="btn-small" onClick={() => setAsking(false)}>
        {t("common.no")}
      </button>
    </span>
  );
}

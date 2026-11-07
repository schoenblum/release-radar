import { useTranslation } from "react-i18next";

import type { Researcher, Unit } from "../api/types";

/** A researcher record with what tells it apart from a namesake (R6.3.4). */
export default function RecordSummary({ record, units }: { record: Researcher; units: Unit[] }) {
  const { t, i18n } = useTranslation();
  const unit = units.find((item) => item.id === record.current_unit_id);
  const unitName = unit ? (i18n.language === "ja" && unit.name_ja) || unit.name_en : null;
  const details = [
    unitName,
    record.orcid,
    record.notes,
    t("researchers.release_total", { count: record.release_count }),
  ].filter(Boolean);
  return (
    <span>
      {record.name} <span className="text-sm text-content-secondary">{details.join(" · ")}</span>
    </span>
  );
}

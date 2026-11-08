import { useState } from "react";
import { useTranslation } from "react-i18next";

import { http } from "../../api/client";
import type { LandingView, ReleaseExportRequest, ReleaseFilters } from "../../api/types";
import ExportPopover, { Choice, type ExportChoice } from "../../components/ExportPopover";

type Scope = "view" | "everything";

/** Export (R7.6.2): what is on screen or everything, as Excel or CSV, in English or Japanese. */
export default function ExportMenu({
  view,
  filters,
  order,
  shown,
}: {
  view: LandingView;
  filters: ReleaseFilters;
  /** The releases in the order the grid shows them. */
  order: string[];
  shown: number;
}) {
  const { t } = useTranslation();
  const [scope, setScope] = useState<Scope>("view");

  async function download({ format, language }: ExportChoice): Promise<void> {
    const body: ReleaseExportRequest =
      scope === "view"
        ? { format, language, filters: { view, ...filters }, order }
        : { format, language, order: [] };
    await http.download("/releases/export", `release_radar_releases.${format}`, body);
  }

  return (
    <ExportPopover
      title={t("data.export.title")}
      xlsxLabel={t("data.export.xlsx")}
      notice={t("data.export.personal_data")}
      download={download}
    >
      <Choice
        name="export-scope"
        legend={t("data.export.rows")}
        value={scope}
        options={[
          { value: "view", label: t("data.export.this_view", { count: shown }) },
          { value: "everything", label: t("data.export.everything") },
        ]}
        onChange={setScope}
      />
    </ExportPopover>
  );
}

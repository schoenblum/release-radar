import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { http } from "../../api/client";
import type { AnalysisTop } from "../../api/types";
import ErrorNotice from "../../components/ErrorNotice";
import ExportPopover, { type ExportChoice } from "../../components/ExportPopover";
import { PageLoading } from "../../components/Spinner";
import { AnalysisHeader, useOptions } from "./AnalysisLayout";
import { AltmetricBasis } from "./DimensionCard";
import { cardLabel, named, type Language } from "./labels";
import RankingTable from "./RankingTable";
import { queryOf } from "./state";
import { useTop } from "./useAnalysis";

const BY_PARAM = "by";

/**
 * The five highest and five lowest shown releases by the default score or any dimension
 * (phase-2 brief §5.4). Only finished releases with a value count, so a provisional one or one
 * with too little data for a score never lands at the bottom. Neutral wording and colours.
 */
export default function TopBottom() {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  const [params, setParams] = useSearchParams();
  const options = useOptions();
  const asked = params.get(BY_PARAM);
  const by = asked && options.pages.some((page) => page.key === asked) ? asked : (options.pages[0]?.key ?? "score");
  const { data, error, isLoading } = useTop(by);

  if (isLoading) return <PageLoading />;
  if (!data) return <ErrorNotice error={error} />;
  const top: AnalysisTop = data;
  const { scope } = top;
  const label = cardLabel(top, language, scope.profile);
  const isScore = top.key === "score";

  async function download({ format, language: chosen }: ExportChoice): Promise<void> {
    const query = queryOf(params, { dimension: by, format, language: chosen });
    await http.download(`/analysis/top/export${query}`, `release_radar_top_${by.replaceAll(".", "_")}.${format}`);
  }

  return (
    <div>
      <AnalysisHeader
        title={t("analysis.top.title")}
        intro={t("analysis.top.intro")}
        scope={scope}
        actions={
          <ExportPopover
            title={t("analysis.export_title", { name: t("analysis.top.title") })}
            xlsxLabel={t("analysis.export_xlsx")}
            notice={t("analysis.export_notice")}
            download={download}
          />
        }
      />
      <ErrorNotice error={error} />
      <div className="mb-3xs flex flex-wrap items-center gap-4xs">
        <label className="flex items-center gap-5xs text-sm">
          <span>{t("analysis.top.by")}</span>
          <select
            className="filter-select"
            value={by}
            onChange={(event) =>
              setParams((current) => {
                const next = new URLSearchParams(current);
                if (event.target.value === options.pages[0]?.key) next.delete(BY_PARAM);
                else next.set(BY_PARAM, event.target.value);
                return next;
              })
            }
          >
            {options.pages.map((page) => (
              <option key={page.key} value={page.key}>
                {page.key === "score" && scope.profile
                  ? cardLabel({ key: "score", label_en: "", label_ja: "" }, language, scope.profile)
                  : named(language, page.label_en, page.label_ja)}
              </option>
            ))}
          </select>
        </label>
        {by === "altmetric" && <AltmetricBasis scope={scope} />}
      </div>
      <p className="mb-3xs max-w-3xl text-sm">{t("analysis.top.caption", { name: label })}</p>

      <h2 className="mb-4xs text-2xl">{t("analysis.top.highest")}</h2>
      {top.highest.length ? (
        <RankingTable
          rows={top.highest}
          options={options}
          decimals={top.decimals}
          isScore={isScore}
          label={label}
          caption={t("analysis.top.highest_caption", { name: label })}
          sortable={false}
        />
      ) : (
        <p className="text-content-secondary">{t("analysis.top.none")}</p>
      )}

      <h2 className="mb-4xs mt-s text-2xl">{t("analysis.top.lowest")}</h2>
      {top.lowest.length ? (
        <RankingTable
          rows={top.lowest}
          options={options}
          decimals={top.decimals}
          isScore={isScore}
          label={label}
          caption={t("analysis.top.lowest_caption", { name: label })}
          sortable={false}
        />
      ) : (
        <p className="text-content-secondary">
          {top.highest.length ? t("analysis.top.lowest_none") : t("analysis.top.none")}
        </p>
      )}
    </div>
  );
}

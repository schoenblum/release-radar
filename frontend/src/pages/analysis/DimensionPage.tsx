import { useTranslation } from "react-i18next";
import { useParams, useSearchParams } from "react-router-dom";

import { http } from "../../api/client";
import ErrorNotice from "../../components/ErrorNotice";
import ExportPopover, { type ExportChoice } from "../../components/ExportPopover";
import { PageLoading } from "../../components/Spinner";
import { AnalysisHeader, useOptions } from "./AnalysisLayout";
import ChartBlock from "./ChartBlock";
import { AltmetricBasis, LogScaleToggle } from "./DimensionCard";
import { cardDescription, cardLabel, type Language } from "./labels";
import RankingTable from "./RankingTable";
import { queryOf, RELEASE_PARAM } from "./state";
import { useDimension, useLogScale } from "./useAnalysis";

/**
 * One dimension (phase-2 brief §5.3): the card's chart, larger, then the ranked list of shown
 * releases, sortable by any column, and its export.
 */
export default function DimensionPage() {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  const { key = "" } = useParams();
  const [params] = useSearchParams();
  const options = useOptions();
  const known = options.pages.some((page) => page.key === key);
  const { data, error, isLoading } = useDimension(key);
  const [isLog, setLog] = useLogScale();

  if (!known) return <p role="alert">{t("analysis.unknown_page")}</p>;
  if (isLoading) return <PageLoading />;
  if (!data) return <ErrorNotice error={error} />;
  const { scope, card, rows } = data;
  const label = cardLabel(card, language, scope.profile);
  const isScore = key === "score";
  // A release picked out from All releases: clicked on the chart, and marked in the ranking.
  const picked = params.get(RELEASE_PARAM);

  async function download({ format, language: chosen }: ExportChoice): Promise<void> {
    const query = queryOf(params, { format, language: chosen });
    await http.download(
      `/analysis/dimensions/${encodeURIComponent(key)}/export${query}`,
      `release_radar_analysis_${key.replaceAll(".", "_")}.${format}`,
    );
  }

  return (
    <div>
      <AnalysisHeader
        title={label}
        intro={cardDescription(t, key, scope.profile)}
        scope={scope}
        actions={
          <ExportPopover
            title={t("analysis.export_title", { name: label })}
            xlsxLabel={t("analysis.export_xlsx")}
            notice={t("analysis.export_notice")}
            download={download}
          />
        }
      />
      <ErrorNotice error={error} />
      <section className="analysis-card analysis-card-wide" aria-label={t("analysis.chart_label", { name: label })}>
        <div className="mb-4xs flex flex-wrap items-center gap-4xs">
          {key === "altmetric" && <AltmetricBasis scope={scope} />}
          {card.box && (
            <LogScaleToggle on={isLog(key)} onChange={(on) => setLog(key, on)} label={label} />
          )}
        </div>
        <ChartBlock card={card} scope={scope} logScale={isLog(key)} large selectedId={picked} />
      </section>
      <h2 className="mb-4xs mt-s text-2xl">{t("analysis.ranking")}</h2>
      <p className="mb-4xs max-w-3xl text-sm text-content-secondary">
        {isScore
          ? t("analysis.ranking_hint_score")
          : t("analysis.ranking_hint", { years: scope.profile?.comparison_years ?? 3 })}
      </p>
      <RankingTable
        rows={rows}
        options={options}
        decimals={card.decimals}
        isScore={isScore}
        label={label}
        caption={t("analysis.ranking_caption", { name: label })}
        picked={picked}
      />
    </div>
  );
}

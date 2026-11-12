import { useTranslation } from "react-i18next";

import ErrorNotice from "../../components/ErrorNotice";
import { PageLoading } from "../../components/Spinner";
import { AnalysisHeader } from "./AnalysisLayout";
import DimensionCard from "./DimensionCard";
import { useLogScale, useOverview } from "./useAnalysis";

/**
 * How the releases did, one card per dimension with data, the score first (phase-2 brief §5.2).
 * The box always describes the analysed releases; the points are the shown ones.
 */
export default function Overview() {
  const { t } = useTranslation();
  const { data, error, isLoading } = useOverview();
  const [isLog, setLog] = useLogScale();
  if (isLoading) return <PageLoading />;
  if (!data) return <ErrorNotice error={error} />;
  const { scope, cards } = data;

  return (
    <div>
      <AnalysisHeader
        title={t("analysis.overview.title")}
        intro={t("analysis.overview.intro")}
        scope={scope}
      />
      <ErrorNotice error={error} />
      <section className="analysis-count-card" aria-label={t("analysis.overview.count_label")}>
        <div className="analysis-card-rule" />
        <p className="text-sm text-content-secondary">{t("analysis.overview.releases")}</p>
        <p className="analysis-big-number">{scope.shown_count}</p>
        <p className="text-sm text-content-secondary">
          {scope.shown_count === scope.analysed_count
            ? t("analysis.overview.all_analysed")
            : t("analysis.overview.of_analysed", { count: scope.analysed_count })}
        </p>
      </section>
      <h2 className="mb-4xs mt-s text-2xl">{t("analysis.overview.dimensions")}</h2>
      <div className="analysis-grid">
        {cards.map((card) => (
          <DimensionCard
            key={card.key}
            card={card}
            scope={scope}
            logScale={isLog(card.key)}
            onLogScale={(on) => setLog(card.key, on)}
          />
        ))}
      </div>
    </div>
  );
}

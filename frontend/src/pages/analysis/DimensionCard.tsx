import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import type { AnalysisCard, AnalysisScope, AnalysisYearMedian } from "../../api/types";
import ChartBlock from "./ChartBlock";
import { cardDescription, cardLabel, type Language } from "./labels";
import { ALTMETRIC_PARAM, pagePath } from "./state";

/** Increase or day 28: the profile's basis by default, the other one a click away. */
export function AltmetricBasis({ scope }: { scope: AnalysisScope }) {
  const { t } = useTranslation();
  const [, setParams] = useSearchParams();
  const profileBasis = scope.profile?.altmetric_basis ?? "increase";
  function choose(basis: "increase" | "d28"): void {
    setParams((current) => {
      const next = new URLSearchParams(current);
      if (basis === profileBasis) next.delete(ALTMETRIC_PARAM);
      else next.set(ALTMETRIC_PARAM, basis);
      return next;
    });
  }
  return (
    <div role="group" aria-label={t("analysis.card.basis")} className="view-toggle">
      {(["increase", "d28"] as const).map((basis) => (
        <button
          key={basis}
          type="button"
          aria-pressed={scope.altmetric_basis === basis}
          className={scope.altmetric_basis === basis ? "view-toggle-on" : "view-toggle-off"}
          onClick={() => choose(basis)}
        >
          {t(`analysis.card.basis_${basis}`)}
        </button>
      ))}
    </div>
  );
}

export function LogScaleToggle({
  on,
  onChange,
  label,
}: {
  on: boolean;
  onChange: (on: boolean) => void;
  label: string;
}) {
  const { t } = useTranslation();
  return (
    <label className="flex items-center gap-5xs text-sm" title={t("analysis.card.log_hint")}>
      <input
        type="checkbox"
        checked={on}
        aria-label={t("analysis.card.log_label", { name: label })}
        onChange={(event) => onChange(event.target.checked)}
      />
      {t("analysis.card.log")}
    </label>
  );
}

/** One card on the overview (phase-2 brief §5.2). */
export default function DimensionCard({
  card,
  scope,
  logScale,
  onLogScale,
  years,
}: {
  card: AnalysisCard;
  scope: AnalysisScope;
  logScale: boolean;
  onLogScale: (on: boolean) => void;
  /** The score's median per academic year: the card shows the score over time. */
  years?: AnalysisYearMedian[];
}) {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  const [params] = useSearchParams();
  const label = cardLabel(card, language, scope.profile);
  const description = cardDescription(t, card.key, scope.profile);
  const headingId = `card-${card.key.replaceAll(".", "-")}`;

  return (
    <section className="analysis-card" aria-labelledby={headingId}>
      <div className="analysis-card-rule" />
      <h2 id={headingId} className="text-xl">
        {label}
      </h2>
      {description && <p className="mb-4xs text-sm text-content-secondary">{description}</p>}
      <div className="mb-4xs flex flex-wrap items-center gap-4xs">
        {card.key === "altmetric" && <AltmetricBasis scope={scope} />}
        {card.box && !years && (
          <LogScaleToggle on={logScale} onChange={onLogScale} label={label} />
        )}
      </div>
      <ChartBlock card={card} scope={scope} logScale={logScale} years={years} />
      <Link className="analysis-open mt-auto" to={pagePath(card.key, params)}>
        {t("analysis.card.open")}
        <span className="sr-only"> {label}</span>
        <span aria-hidden="true"> →</span>
      </Link>
    </section>
  );
}

import { useCallback, useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type {
  AnalysisCard,
  AnalysisPoint,
  AnalysisScope,
  AnalysisYearMedian,
} from "../../api/types";
import { academicYearLabel } from "../../dates";
import BoxStrip from "./BoxStrip";
import {
  caption,
  cardLabel,
  countLine,
  formatValue,
  type Language,
} from "./labels";
import ScoreOverTime from "./ScoreOverTime";

/** A point's hover text: code, title, value. */
export function usePointWords(decimals: number): (point: AnalysisPoint) => string {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  return useCallback(
    (point: AnalysisPoint) =>
      [point.code, point.title, formatValue(point.value, decimals, language)]
        .filter(Boolean)
        .join(" · ") + (point.inferred ? ` (${t("data.inferred")})` : ""),
    [decimals, language, t],
  );
}

/**
 * A dimension's chart with what it shows in words: lowest, median and highest, a plain caption,
 * the count line, and the same numbers as a table for keyboards and screen readers.
 */
export default function ChartBlock({
  card,
  scope,
  logScale,
  large = false,
  years,
  selectedId,
}: {
  card: AnalysisCard;
  scope: AnalysisScope;
  logScale: boolean;
  large?: boolean;
  /** The score's median per academic year: drawn over time instead of as a box. */
  years?: AnalysisYearMedian[];
  /** A release to show as clicked. */
  selectedId?: string | null;
}) {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  const [asTable, setAsTable] = useState(false);
  const tableId = useId();
  const show = (value: number): string =>
    formatValue(value, card.decimals, language);
  // The points are the population's shown members; when every member is shown, one set.
  const sameSet = card.box !== null && card.points.length === card.box.n;
  const measure = cardLabel(card, language, scope.profile);
  const words =
    years !== undefined
      ? t("analysis.score_time.caption", {
          medians: years
            .map((year) =>
              t("analysis.score_time.median", {
                year: academicYearLabel(year.year, language),
                median: show(year.median),
              }),
            )
            .join(t("analysis.answers.separator")),
        })
      : caption(t, language, card, sameSet, logScale);
  const describe = usePointWords(card.decimals);

  return (
    <div>
      {years !== undefined && card.box ? (
        <ScoreOverTime
          points={card.points}
          years={years}
          label={words}
          measure={measure}
          describe={describe}
        />
      ) : card.box ? (
        <>
          <BoxStrip
            box={card.box}
            points={card.points}
            logScale={logScale}
            size={large ? "large" : "card"}
            label={words}
            describe={describe}
            measure={measure}
            decimals={card.decimals}
            selectedId={selectedId}
          />
          <dl className="analysis-lmh">
            <div>
              <dt>{t("analysis.card.lowest")}</dt>
              <dd>{show(card.box.low)}</dd>
            </div>
            <div className="text-center">
              <dt>{t("analysis.card.median")}</dt>
              <dd className="analysis-median">{show(card.box.median)}</dd>
            </div>
            <div className="text-right">
              <dt>{t("analysis.card.highest")}</dt>
              <dd>{show(card.box.high)}</dd>
            </div>
          </dl>
        </>
      ) : null}
      <p className="mt-4xs text-sm">{words}</p>
      <p className="mt-5xs text-sm text-content-secondary">
        {countLine(t, card)}
        {scope.shown_count !== scope.analysed_count && card.box
          ? ` · ${t("analysis.counts.shown_points", { count: card.points.length })}`
          : ""}
      </p>
      {card.box && (
        <>
          <button
            type="button"
            className="link-button mt-4xs text-sm"
            aria-expanded={asTable}
            aria-controls={tableId}
            onClick={() => setAsTable((current) => !current)}
          >
            {asTable
              ? t("analysis.card.hide_table")
              : t("analysis.card.show_table")}
          </button>
          {asTable && (
            <div id={tableId} className="mt-4xs">
              {years !== undefined && (
                <table className="count-table analysis-summary mb-4xs">
                  <thead>
                    <tr>
                      <th scope="col" className="is-text">
                        {t("analysis.columns.academic_year")}
                      </th>
                      <th scope="col">{t("analysis.card.median")}</th>
                      <th scope="col">{t("analysis.card.analysed_n")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {years.map((year) => (
                      <tr key={year.year}>
                        <th scope="row" className="is-text">
                          {academicYearLabel(year.year, language)}
                        </th>
                        <td>{show(year.median)}</td>
                        <td>{year.n}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {years === undefined && (
                <table className="count-table analysis-summary">
                  <caption className="sr-only">{words}</caption>
                  <tbody>
                    {(
                      [
                        ["lowest", card.box.low],
                        ["q1", card.box.q1],
                        ["median", card.box.median],
                        ["q3", card.box.q3],
                        ["highest", card.box.high],
                      ] as const
                    ).map(([name, value]) => (
                      <tr key={name}>
                        <th scope="row" className="is-text">
                          {t(`analysis.card.${name}`)}
                        </th>
                        <td>{show(value)}</td>
                      </tr>
                    ))}
                    <tr>
                      <th scope="row" className="is-text">
                        {t("analysis.card.analysed_n")}
                      </th>
                      <td>{card.box.n}</td>
                    </tr>
                    {!sameSet && (
                      <tr>
                        <th scope="row" className="is-text">
                          {t("analysis.card.shown_median_label", {
                            count: card.points.length,
                          })}
                        </th>
                        <td>
                          {card.shown_median === null
                            ? "–"
                            : show(card.shown_median)}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              )}
              {card.points.length > 0 && (
                <div className="analysis-points-scroll mt-4xs">
                  <table className="count-table">
                    <thead>
                      <tr>
                        <th scope="col" className="is-text">
                          {t("analysis.columns.code")}
                        </th>
                        <th scope="col" className="is-text">
                          {t("analysis.columns.title")}
                        </th>
                        <th scope="col" className="is-text">
                          {t("analysis.columns.release_date")}
                        </th>
                        <th scope="col">{t("analysis.columns.value")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...card.points]
                        .sort((a, b) => b.value - a.value)
                        .map((point) => (
                          <tr key={point.id}>
                            <th scope="row" className="is-text">
                              {point.code ?? ""}
                            </th>
                            <td className="is-text analysis-title-cell">
                              {point.title ?? ""}
                            </td>
                            <td className="is-text">{point.release_date}</td>
                            <td>
                              {show(point.value)}
                              {point.inferred ? (
                                <span className="grid-badge">
                                  {t("data.inferred")}
                                </span>
                              ) : null}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

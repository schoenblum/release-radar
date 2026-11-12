import { useCallback, useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type { AnalysisCard, AnalysisPoint, AnalysisScope } from "../../api/types";
import BoxStrip from "./BoxStrip";
import { caption, countLine, formatValue, type Language } from "./labels";

/**
 * A dimension's chart with what it shows in words: lowest, median and highest, a plain caption,
 * the count line, and the same numbers as a table for keyboards and screen readers.
 */
export default function ChartBlock({
  card,
  scope,
  logScale,
  large = false,
}: {
  card: AnalysisCard;
  scope: AnalysisScope;
  logScale: boolean;
  large?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  const [asTable, setAsTable] = useState(false);
  const tableId = useId();
  const show = (value: number): string => formatValue(value, card.decimals, language);
  // The points are the population's shown members; when every member is shown, one set.
  const sameSet = card.box !== null && card.points.length === card.box.n;
  const words = caption(t, language, card, sameSet, logScale);
  const describe = useCallback(
    (point: AnalysisPoint) =>
      [point.code, point.title, formatValue(point.value, card.decimals, language)]
        .filter(Boolean)
        .join(" · ") + (point.inferred ? ` (${t("data.inferred")})` : ""),
    [card.decimals, language, t],
  );

  return (
    <div>
      {card.box ? (
        <>
          <BoxStrip
            box={card.box}
            points={card.points}
            logScale={logScale}
            large={large}
            label={words}
            describe={describe}
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
            {asTable ? t("analysis.card.hide_table") : t("analysis.card.show_table")}
          </button>
          {asTable && (
            <div id={tableId} className="mt-4xs">
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
                      <th scope="row">{t(`analysis.card.${name}`)}</th>
                      <td>{show(value)}</td>
                    </tr>
                  ))}
                  <tr>
                    <th scope="row">{t("analysis.card.analysed_n")}</th>
                    <td>{card.box.n}</td>
                  </tr>
                  {!sameSet && (
                    <tr>
                      <th scope="row">{t("analysis.card.shown_median_label", { count: card.points.length })}</th>
                      <td>{card.shown_median === null ? "–" : show(card.shown_median)}</td>
                    </tr>
                  )}
                </tbody>
              </table>
              {card.points.length > 0 && (
                <div className="analysis-points-scroll mt-4xs">
                  <table className="count-table">
                    <thead>
                      <tr>
                        <th scope="col">{t("analysis.columns.code")}</th>
                        <th scope="col">{t("analysis.columns.title")}</th>
                        <th scope="col">{t("analysis.columns.value")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...card.points]
                        .sort((a, b) => b.value - a.value)
                        .map((point) => (
                          <tr key={point.id}>
                            <th scope="row">{point.code ?? ""}</th>
                            <td className="analysis-title-cell">{point.title ?? ""}</td>
                            <td>
                              {show(point.value)}
                              {point.inferred ? <span className="grid-badge">{t("data.inferred")}</span> : null}
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

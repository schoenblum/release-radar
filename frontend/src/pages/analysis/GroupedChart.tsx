import type { TFunction } from "i18next";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import type {
  AnalysisCard,
  AnalysisGroup,
  AnalysisOptions,
  AnalysisPoint,
  AnalysisScope,
  FilterDimension,
} from "../../api/types";
import { useOptions } from "./AnalysisLayout";
import BoxStrip from "./BoxStrip";
import { usePointWords } from "./ChartBlock";
import { cardLabel, countLine, formatValue, optionsOf, valueLabel, type Language } from "./labels";

/** Fewer values than this show a median only (the server's `MIN_BOX`). */
export const MIN_BOX = 5;
// One empty list, so the rows without dots are not drawn again at every render.
const NO_POINTS: AnalysisPoint[] = [];

/**
 * The order groups are read in: years in time; type, embargo and gender as the filters list
 * them; units and fields, which have no order of their own, highest median first.
 */
export function orderGroups(
  by: FilterDimension,
  groups: AnalysisGroup[],
  options: AnalysisOptions,
  name: (value: string) => string,
): AnalysisGroup[] {
  const sorted = [...groups];
  if (by === "ay") return sorted.sort((a, b) => Number(a.value) - Number(b.value));
  if (by === "unit" || by === "field") {
    return sorted.sort(
      (a, b) => b.median - a.median || name(a.value).localeCompare(name(b.value)),
    );
  }
  const order = optionsOf(options, by).map((option) => option.value);
  const place = (value: string): number => {
    const found = order.indexOf(value);
    return found === -1 ? order.length : found;
  };
  return sorted.sort((a, b) => place(a.value) - place(b.value));
}

function caption(
  t: TFunction,
  by: FilterDimension,
  groups: AnalysisGroup[],
  name: (value: string) => string,
  show: (value: number) => string,
  logScale: boolean,
): string {
  const medians = groups
    .map((group) => t("analysis.group.median_of", { name: name(group.value), median: show(group.median) }))
    .join(t("analysis.answers.separator"));
  return [
    t("analysis.group.caption", { group: t(`analysis.group.nouns.${by}`), min: MIN_BOX }),
    t("analysis.group.medians", { medians }),
    logScale ? t("analysis.card.log_on") : "",
  ]
    .filter(Boolean)
    .join(" ");
}

/**
 * A measure split by one grouping (Daniel, 2026-11-12): a row per year, field, unit …, each
 * with its own box over its analysed releases and its shown releases as dots, all on one scale
 * under the box of every analysed release. A group with fewer than five values shows its median
 * only. The same numbers are a table on request.
 */
export default function GroupedChart({
  card,
  groups,
  by,
  scope,
  logScale,
  selectedId,
}: {
  card: AnalysisCard;
  groups: AnalysisGroup[];
  by: FilterDimension;
  scope: AnalysisScope;
  logScale: boolean;
  selectedId?: string | null;
}) {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  const options = useOptions();
  const [asTable, setAsTable] = useState(false);
  const tableId = useId();
  const describe = usePointWords(card.decimals);
  const measure = cardLabel(card, language, scope.profile);
  const show = (value: number): string => formatValue(value, card.decimals, language);
  const name = (value: string): string => valueLabel(t, language, options, by, value);
  const ordered = orderGroups(by, groups, options, name);
  if (!card.box) return <p className="text-sm">{t("analysis.card.no_values")}</p>;
  const domain: [number, number] = [card.box.low, card.box.high];
  const words = caption(t, by, ordered, name, show, logScale);
  const shownPoints = ordered.reduce((sum, group) => sum + group.points.length, 0);
  // The table: every analysed release first, then each group.
  const lines = [
    {
      value: null as string | null,
      n: card.box.n,
      median: card.box.median,
      box: card.box,
      shown: card.shown_median,
      count: card.points.length,
    },
    ...ordered.map((group) => ({
      value: group.value as string | null,
      n: group.n,
      median: group.median,
      box: group.box,
      shown: group.shown_median,
      count: group.points.length,
    })),
  ];

  return (
    <div>
      <div className="group-rows" role="group" aria-label={words}>
        <div className="group-row">
          <p className="group-label">
            {t("analysis.group.all")} <span className="group-count">({card.box.n})</span>
          </p>
          <BoxStrip
            box={card.box}
            points={NO_POINTS}
            size="row"
            domain={domain}
            logScale={logScale}
            label={t("analysis.group.row_label", {
              name: t("analysis.group.all"),
              median: show(card.box.median),
              count: card.box.n,
            })}
            describe={describe}
            measure={measure}
            decimals={card.decimals}
          />
        </div>
        {ordered.map((group) => (
          <div key={group.value} className="group-row">
            <p className="group-label">
              {name(group.value)} <span className="group-count">({group.n})</span>
            </p>
            <BoxStrip
              box={group.box}
              median={group.median}
              points={group.points}
              size="row"
              domain={domain}
              logScale={logScale}
              label={t("analysis.group.row_label", {
                name: name(group.value),
                median: show(group.median),
                count: group.n,
              })}
              describe={describe}
              measure={measure}
              decimals={card.decimals}
              selectedId={selectedId}
              inRanking
            />
          </div>
        ))}
        <div className="group-row" aria-hidden="true">
          <span />
          <BoxStrip
            box={null}
            points={NO_POINTS}
            size="row"
            domain={domain}
            axis
            logScale={logScale}
            label=""
            describe={describe}
            measure={measure}
            decimals={card.decimals}
          />
        </div>
      </div>
      <p className="mt-4xs text-sm">{words}</p>
      <p className="mt-5xs text-sm text-content-secondary">
        {countLine(t, card)}
        {scope.shown_count !== scope.analysed_count
          ? ` · ${t("analysis.counts.shown_points", { count: shownPoints })}`
          : ""}
      </p>
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
        <div id={tableId} className="analysis-points-scroll mt-4xs">
          <table className="count-table">
            <caption className="sr-only">{words}</caption>
            <thead>
              <tr>
                <th scope="col" className="is-text">
                  {t(`analysis.group.options.${by}`)}
                </th>
                <th scope="col">{t("analysis.card.analysed_n")}</th>
                <th scope="col">{t("analysis.card.lowest")}</th>
                <th scope="col">{t("analysis.card.q1")}</th>
                <th scope="col">{t("analysis.card.median")}</th>
                <th scope="col">{t("analysis.card.q3")}</th>
                <th scope="col">{t("analysis.card.highest")}</th>
                <th scope="col">{t("analysis.group.shown_median")}</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line) => (
                <tr key={line.value ?? "all"}>
                  <th scope="row" className="is-text">
                    {line.value === null ? t("analysis.group.all") : name(line.value)}
                  </th>
                  <td>{line.n}</td>
                  <td>{line.box ? show(line.box.low) : "–"}</td>
                  <td>{line.box ? show(line.box.q1) : "–"}</td>
                  <td>{show(line.median)}</td>
                  <td>{line.box ? show(line.box.q3) : "–"}</td>
                  <td>{line.box ? show(line.box.high) : "–"}</td>
                  <td>
                    {line.shown === null
                      ? "–"
                      : t("analysis.group.shown_median_value", { median: show(line.shown), count: line.count })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

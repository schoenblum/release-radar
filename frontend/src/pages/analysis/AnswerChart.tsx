import { useTranslation } from "react-i18next";

import type {
  AnalysisAnswerChart,
  AnalysisOptions,
  AnalysisScope,
  FilterDimension,
} from "../../api/types";
import { useOptions } from "./AnalysisLayout";
import GroupChoice, { GROUPINGS } from "./GroupChoice";
import { named, optionsOf, valueLabel, type Language } from "./labels";
import { answerGroupParam } from "./state";

// Written out whole: Tailwind keeps only the classes it finds in the source, so a name built
// at run time would lose its colour (Daniel saw empty bars, 2026-11-12).
const COLOURS = [
  "answer-colour-0",
  "answer-colour-1",
  "answer-colour-2",
  "answer-colour-3",
  "answer-colour-4",
  "answer-colour-5",
];

/** A survey chart can be split by any grouping but the unit: 23 units would make 23 bars per
 * box, which nobody can read (a measure's page splits by unit as rows instead). */
const ANSWER_GROUPINGS = GROUPINGS.filter((grouping) => grouping !== "unit");

/**
 * A survey question as bars (Daniel, 2026-11-12): for each box, the share of the shown
 * releases whose researchers ticked it, among those who answered the question. Both filters
 * decide which releases count. When fewer are shown than analysed, a second bar gives the
 * analysed releases to compare with; split by a grouping (year, field …), one bar per group.
 *
 * Plain HTML rather than a Plot chart: the labels are long sentences, in Japanese too, and wrap
 * here as text does; the bars are their widths.
 */
export default function AnswerChart({
  chart,
  scope,
}: {
  chart: AnalysisAnswerChart;
  scope: AnalysisScope;
}) {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  const options = useOptions();
  const headingId = `answers-${chart.question}`;
  const title = t(`analysis.answers.${chart.question}.title`);
  const seriesName = (key: string): string =>
    chart.by
      ? valueLabel(t, language, options, chart.by, key)
      : t(`analysis.answers.series.${key === "analysed" ? "analysed" : "shown"}`);
  const several = chart.series.length > 1;
  const series = chart.by ? orderSeries(chart.by, chart.series, options) : chart.series;
  const place = new Map(series.map((item, index) => [item.key, index]));
  const respondents = series
    .map((item) =>
      t("analysis.answers.respondents", { name: seriesName(item.key), count: item.respondents }),
    )
    .join(t("analysis.answers.separator"));

  return (
    <section className="analysis-card" aria-labelledby={headingId}>
      <div className="analysis-card-rule" />
      <h3 id={headingId} className="text-xl">
        {title}
      </h3>
      <p className="mb-4xs text-sm text-content-secondary">
        {t(`analysis.answers.${chart.question}.describe`)}
      </p>
      <div className="mb-4xs">
        <GroupChoice
          param={answerGroupParam(chart.question)}
          scope={scope}
          offered={ANSWER_GROUPINGS}
          label={t("analysis.group.label_for", { name: title })}
        />
      </div>
      {several && (
        <ul className="answer-legend" aria-hidden="true">
          {series.map((item, index) => (
            <li key={item.key}>
              <span className={`answer-swatch ${COLOURS[index % COLOURS.length]}`} />
              {seriesName(item.key)}
            </li>
          ))}
        </ul>
      )}
      <dl className="answer-bars">
        {chart.bars.map((bar) => (
          <div key={bar.key} className="answer-row">
            <dt>{named(language, bar.label_en, bar.label_ja)}</dt>
            {[...bar.shares]
              .sort((a, b) => (place.get(a.series) ?? 0) - (place.get(b.series) ?? 0))
              .map((share) => {
                const index = place.get(share.series) ?? 0;
                const total = series[index]?.respondents ?? 0;
                const words = t("analysis.answers.bar", {
                  name: seriesName(share.series),
                  share: Math.round(share.share),
                  count: share.count,
                  total,
                });
                return (
                  <dd key={share.series} className="answer-line" title={words}>
                    <span className="sr-only">{words}</span>
                    <span className="answer-track" aria-hidden="true">
                      <span
                        className={`answer-fill ${COLOURS[index % COLOURS.length]}`}
                        style={{ width: `${share.share}%` }}
                      />
                    </span>
                    <span className="answer-share" aria-hidden="true">
                      {Math.round(share.share)}%
                    </span>
                  </dd>
                );
              })}
          </div>
        ))}
      </dl>
      <p className="mt-4xs text-sm">
        {several
          ? t("analysis.answers.caption", { respondents })
          : t("analysis.answers.caption_one", { count: series[0]?.respondents ?? 0 })}
      </p>
    </section>
  );
}

/** Groups in reading order: years in time, the rest as the filters list them. */
function orderSeries(
  by: FilterDimension,
  series: AnalysisAnswerChart["series"],
  options: AnalysisOptions,
): AnalysisAnswerChart["series"] {
  if (by === "ay") return [...series].sort((a, b) => Number(a.key) - Number(b.key));
  const order = optionsOf(options, by).map((option) => option.value);
  const place = (key: string): number => {
    const found = order.indexOf(key);
    return found === -1 ? order.length : found;
  };
  return [...series].sort((a, b) => place(a.key) - place(b.key));
}

import { useTranslation } from "react-i18next";

import type { AnalysisAnswerChart } from "../../api/types";
import { academicYearLabel } from "../../dates";
import { named, type Language } from "./labels";

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

/**
 * A survey question as bars (Daniel, 2026-11-12): for each box, the share of the analysed
 * releases whose researchers ticked it, among those who answered the question. With more than
 * one academic year, one bar per year, so years compare as on the office's report.
 *
 * Plain HTML rather than a Plot chart: the labels are long sentences, in Japanese too, and wrap
 * here as text does; the bars are their widths.
 */
export default function AnswerChart({ chart }: { chart: AnalysisAnswerChart }) {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  const headingId = `answers-${chart.question}`;
  const year = (value: number) => academicYearLabel(value, language);
  const several = chart.years.length > 1;
  const respondents = chart.years
    .map((item) => t("analysis.answers.respondents", { year: year(item.year), count: item.respondents }))
    .join(t("analysis.answers.separator"));

  return (
    <section className="analysis-card" aria-labelledby={headingId}>
      <div className="analysis-card-rule" />
      <h3 id={headingId} className="text-xl">
        {t(`analysis.answers.${chart.question}.title`)}
      </h3>
      <p className="mb-4xs text-sm text-content-secondary">
        {t(`analysis.answers.${chart.question}.describe`)}
      </p>
      {several && (
        <ul className="answer-legend" aria-hidden="true">
          {chart.years.map((item, index) => (
            <li key={item.year}>
              <span className={`answer-swatch ${COLOURS[index % COLOURS.length]}`} />
              {year(item.year)}
            </li>
          ))}
        </ul>
      )}
      <dl className="answer-bars">
        {chart.bars.map((bar) => (
          <div key={bar.key} className="answer-row">
            <dt>{named(language, bar.label_en, bar.label_ja)}</dt>
            {bar.shares.map((share, index) => {
              const respondentsThatYear =
                chart.years.find((item) => item.year === share.year)?.respondents ?? 0;
              const words = t("analysis.answers.bar", {
                year: year(share.year),
                share: Math.round(share.share),
                count: share.count,
                total: respondentsThatYear,
              });
              return (
                <dd key={share.year} className="answer-line" title={words}>
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
      <p className="mt-4xs text-sm">{t("analysis.answers.caption", { respondents })}</p>
    </section>
  );
}

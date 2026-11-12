import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { http } from "../../api/client";
import type { AnalysisAnswerChart, AnalysisAnswers, AnalysisOptions } from "../../api/types";
import ErrorNotice from "../../components/ErrorNotice";
import ExportPopover, { type ExportChoice } from "../../components/ExportPopover";
import { PageLoading } from "../../components/Spinner";
import { AnalysisHeader, useOptions } from "./AnalysisLayout";
import { AnswerBars } from "./AnswerChart";
import GroupChoice, { ANSWER_GROUPINGS } from "./GroupChoice";
import { named, type Language } from "./labels";
import { listName, recordLink } from "./RankingTable";
import { GROUP_PARAM, queryOf } from "./state";
import { useAnswers } from "./useAnalysis";

type Row = AnalysisAnswers["rows"][number];
type Question = AnalysisAnswerChart["question"];
/** A column: one of these, or `box:<key>` for a survey box. */
type Column = "code" | "title" | "release_date" | "unit" | "ticked" | `box:${string}`;

const TEXT_COLUMNS = new Set<Column>(["code", "title", "unit"]);

/**
 * The releases under a survey question's bars (Daniel, 2026-11-13): every shown release with
 * the boxes its researchers ticked. A list, not a ranking, since a release is not better for
 * more boxes ticked: newest first, sortable by any column, so a click on a box's heading puts
 * the releases that ticked it first. Releases without an answer stay in the list, last, so the
 * gaps are visible.
 */
function AnswerTable({
  rows,
  choices,
  options,
  caption,
}: {
  rows: Row[];
  choices: AnalysisAnswers["choices"];
  options: AnalysisOptions;
  caption: string;
}) {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  const [sort, setSort] = useState<{ column: Column; desc: boolean }>({
    column: "release_date",
    desc: true,
  });
  const columns: Column[] = [
    "code",
    "title",
    "release_date",
    "unit",
    ...choices.map((choice) => `box:${choice.key}` as Column),
    "ticked",
  ];

  const ordered = useMemo(() => {
    const value = (row: Row, column: Column): string | number => {
      if (column.startsWith("box:")) return row.ticked.includes(column.slice(4)) ? 1 : 0;
      if (column === "ticked") return row.ticked.length;
      if (column === "unit") return listName(options.units, row.unit_id, language);
      if (column === "code") return row.code ?? "";
      if (column === "title") return row.title ?? "";
      return row.release_date;
    };
    return [...rows].sort((a, b) => {
      // Without an answer, last whichever way round: there is nothing to compare.
      if (a.answered !== b.answered) return a.answered ? -1 : 1;
      const left = value(a, sort.column);
      const right = value(b, sort.column);
      const order =
        typeof left === "number" && typeof right === "number"
          ? left - right
          : String(left).localeCompare(String(right), language);
      return (sort.desc ? -order : order) || b.release_date.localeCompare(a.release_date);
    });
  }, [rows, sort, options.units, language]);

  function heading(column: Column): string {
    if (column.startsWith("box:")) {
      const choice = choices.find((item) => item.key === column.slice(4));
      return choice ? named(language, choice.label_en, choice.label_ja) : column;
    }
    if (column === "ticked") return t("analysis.answers.columns.ticked");
    return t(`analysis.columns.${column as "code" | "title" | "release_date" | "unit"}`);
  }

  function choose(column: Column): void {
    setSort((current) =>
      current.column === column
        ? { column, desc: !current.desc }
        : // Boxes, counts and dates read best from the top: ticked, most, newest first.
          { column, desc: !TEXT_COLUMNS.has(column) },
    );
  }

  return (
    <div className="table-scroll">
      <table className="count-table rank-table">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => {
              const active = sort.column === column;
              const box = column.startsWith("box:");
              return (
                <th
                  key={column}
                  scope="col"
                  className={TEXT_COLUMNS.has(column) ? "is-text" : box ? "answer-head" : undefined}
                  aria-sort={active ? (sort.desc ? "descending" : "ascending") : undefined}
                >
                  <button type="button" className="sort-button" onClick={() => choose(column)}>
                    {heading(column)}
                    <span aria-hidden="true">{active ? (sort.desc ? " ▼" : " ▲") : ""}</span>
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {ordered.map((row) => (
            <tr key={row.id} className={row.answered ? undefined : "is-empty"}>
              <th scope="row" className="is-text">
                {row.code ?? ""}
              </th>
              <td className="is-text analysis-title-cell">
                <Link to={recordLink(row.id)}>{row.title || t("data.no_title")}</Link>
              </td>
              <td>{row.release_date}</td>
              <td className="is-text">{listName(options.units, row.unit_id, language)}</td>
              {choices.map((choice) => {
                const ticked = row.ticked.includes(choice.key);
                return (
                  <td key={choice.key} className="answer-cell">
                    {ticked ? (
                      <>
                        <span aria-hidden="true">✓</span>
                        <span className="sr-only">{t("analysis.answers.ticked")}</span>
                      </>
                    ) : null}
                  </td>
                );
              })}
              <td className={row.answered ? undefined : "text-content-secondary"}>
                {row.answered ? row.ticked.length : t("analysis.answers.no_answer")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * A survey question's own page (Daniel, 2026-11-13), as each measure has one: its bars for the
 * releases the filters select, split by year, type, field, embargo or gender on request, and
 * the releases below with what their researchers ticked.
 */
export default function AnswersPage() {
  const { t } = useTranslation();
  const { question: asked = "" } = useParams();
  const [params] = useSearchParams();
  const options = useOptions();
  const known = (options.answers as string[]).includes(asked);
  const question = asked as Question;
  const { data, error, isLoading } = useAnswers(question);

  if (!known) return <p role="alert">{t("analysis.unknown_page")}</p>;
  if (isLoading) return <PageLoading />;
  if (!data) return <ErrorNotice error={error} />;
  const { scope, chart, rows, choices } = data;
  const title = t(`analysis.answers.${question}.title`);
  const answered = rows.filter((row) => row.answered).length;

  async function download({ format, language: chosen }: ExportChoice): Promise<void> {
    const query = queryOf(params, { format, language: chosen });
    await http.download(
      `/analysis/answers/${encodeURIComponent(question)}/export${query}`,
      `release_radar_answers_${question}.${format}`,
    );
  }

  return (
    <div>
      <AnalysisHeader
        title={title}
        intro={t(`analysis.answers.${question}.intro`)}
        scope={scope}
        actions={
          <ExportPopover
            title={t("analysis.export_title", { name: title })}
            xlsxLabel={t("analysis.export_xlsx")}
            notice={t("analysis.export_notice")}
            download={download}
          />
        }
      />
      <ErrorNotice error={error} />
      <section
        className="analysis-card analysis-card-wide"
        aria-label={t("analysis.chart_label", { name: title })}
      >
        <div className="mb-4xs flex flex-wrap items-center gap-x-xs gap-y-4xs">
          <GroupChoice param={GROUP_PARAM} scope={scope} offered={ANSWER_GROUPINGS} />
        </div>
        {chart ? (
          <AnswerBars chart={chart} />
        ) : (
          <p className="text-sm">{t("analysis.answers.none_answered")}</p>
        )}
      </section>
      <h2 className="mb-4xs mt-s text-2xl">{t("analysis.answers.list_heading")}</h2>
      <p className="mb-4xs max-w-3xl text-sm text-content-secondary">
        {t("analysis.answers.list_hint", { answered, shown: rows.length })}
      </p>
      <AnswerTable
        rows={rows}
        choices={choices}
        options={options}
        caption={t("analysis.answers.list_caption", { name: title })}
      />
    </div>
  );
}

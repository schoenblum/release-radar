import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import type { AnalysisEntry, AnalysisOptions } from "../../api/types";
import { formatValue, named, type Language } from "./labels";

type Column =
  | "rank"
  | "code"
  | "title"
  | "release_date"
  | "unit"
  | "field"
  | "value"
  | "percentile"
  | "coverage"
  | "based_on"
  | "state";

// Words read from the left; numbers line up on the right.
const TEXT_COLUMNS = new Set<Column>(["code", "title", "unit", "field", "based_on", "state"]);

/** The record opens on the Data page, in the All view, where every release is listed. */
/** A ranking row's own address in the page, which a chart's window scrolls to. */
export function rankingRowId(releaseId: string): string {
  return `rank-${releaseId}`;
}

export function recordLink(id: string): string {
  return `/data?${new URLSearchParams({ view: "all", release: id }).toString()}`;
}

export function componentNames(
  entry: AnalysisEntry,
  options: AnalysisOptions,
  language: Language,
): string {
  return entry.components
    .map((key) => {
      const page = options.pages.find((item) => item.key === key);
      return page ? named(language, page.label_en, page.label_ja) : key;
    })
    .join(", ");
}

function listName(
  options: AnalysisOptions["units"],
  id: string | null,
  language: Language,
): string {
  if (id === null) return "";
  const found = options.find((option) => option.value === id);
  return found ? named(language, found.short_en ?? found.label_en, found.label_ja) : "";
}

/**
 * A ranked list of releases (phase-2 brief §5.3): sortable by any column, rows without a value
 * last whichever way round, provisional ones marked.
 */
export default function RankingTable({
  rows,
  options,
  decimals,
  isScore,
  label,
  caption,
  sortable = true,
  picked = null,
}: {
  rows: AnalysisEntry[];
  options: AnalysisOptions;
  decimals: number;
  isScore: boolean;
  label: string;
  caption: string;
  sortable?: boolean;
  /** A release picked out, as from All releases: its row stands out. */
  picked?: string | null;
}) {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  const [sort, setSort] = useState<{ column: Column; desc: boolean }>({ column: "rank", desc: false });

  const columns: Column[] = isScore
    ? ["rank", "code", "title", "release_date", "unit", "field", "value", "coverage", "based_on", "state"]
    : ["rank", "code", "title", "release_date", "unit", "field", "value", "percentile", "state"];

  const sortValue = useMemo(
    () =>
      (entry: AnalysisEntry, column: Column): string | number | null => {
        switch (column) {
          case "rank":
            return entry.rank;
          case "code":
            return entry.code;
          case "title":
            return entry.title;
          case "release_date":
            return entry.release_date;
          case "unit":
            return listName(options.units, entry.unit_id, language) || null;
          case "field":
            return listName(options.fields, entry.field_id, language) || null;
          case "value":
            return entry.value;
          case "percentile":
            return entry.percentile;
          case "coverage":
            return entry.coverage;
          case "based_on":
            return componentNames(entry, options, language) || null;
          case "state":
            return t(`analysis.states.${entry.state}`);
        }
      },
    [language, options, t],
  );

  const ordered = useMemo(() => {
    if (!sortable) return rows;
    const collator = new Intl.Collator(language, { numeric: true, sensitivity: "base" });
    return [...rows].sort((a, b) => {
      const left = sortValue(a, sort.column);
      const right = sortValue(b, sort.column);
      if (left === null || right === null) {
        return left === right ? 0 : left === null ? 1 : -1;
      }
      const order =
        typeof left === "number" && typeof right === "number"
          ? left - right
          : collator.compare(String(left), String(right));
      return sort.desc ? -order : order;
    });
  }, [language, rows, sort, sortValue, sortable]);

  function heading(column: Column): string {
    if (column === "value") return label;
    return t(`analysis.columns.${column}`);
  }

  function choose(column: Column): void {
    setSort((current) =>
      current.column === column
        ? { column, desc: !current.desc }
        : // Numbers read best highest first; the rank and text, from the top.
          { column, desc: column === "value" || column === "percentile" || column === "coverage" },
    );
  }

  return (
    <div className="table-scroll">
      <table className="count-table rank-table">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => {
              const active = sortable && sort.column === column;
              return (
                <th
                  key={column}
                  scope="col"
                  className={TEXT_COLUMNS.has(column) ? "is-text" : undefined}
                  aria-sort={active ? (sort.desc ? "descending" : "ascending") : undefined}
                >
                  {sortable ? (
                    <button type="button" className="sort-button" onClick={() => choose(column)}>
                      {heading(column)}
                      <span aria-hidden="true">{active ? (sort.desc ? " ▼" : " ▲") : ""}</span>
                    </button>
                  ) : (
                    heading(column)
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {ordered.map((entry) => (
            <tr
              key={entry.id}
              id={rankingRowId(entry.id)}
              className={
                [entry.value === null ? "is-empty" : "", entry.id === picked ? "is-picked" : ""]
                  .filter(Boolean)
                  .join(" ") || undefined
              }
            >
              <td>{entry.rank ?? "–"}</td>
              <th scope="row" className="is-text">
                {entry.code ?? ""}
              </th>
              <td className="is-text analysis-title-cell">
                <Link to={recordLink(entry.id)}>{entry.title || t("data.no_title")}</Link>
                {entry.provisional && (
                  <span className="grid-badge" title={t("analysis.provisional_hint")}>
                    {t("analysis.provisional")}
                  </span>
                )}
              </td>
              <td>{entry.release_date}</td>
              <td className="is-text">{listName(options.units, entry.unit_id, language)}</td>
              <td className="is-text">{listName(options.fields, entry.field_id, language)}</td>
              <td>
                {entry.value === null ? "" : formatValue(entry.value, decimals, language)}
                {entry.inferred && (
                  <span className="grid-badge" title={t("data.inferred_why")}>
                    {t("data.inferred")}
                  </span>
                )}
              </td>
              {isScore ? (
                <>
                  <td>{entry.coverage === null ? "" : `${Math.round(entry.coverage * 100)} %`}</td>
                  <td className="is-text analysis-based-on">
                    {componentNames(entry, options, language)}
                  </td>
                </>
              ) : (
                <td title={entry.percentile === null && entry.value !== null ? t("analysis.too_few") : undefined}>
                  {entry.percentile === null ? "" : Math.round(entry.percentile)}
                </td>
              )}
              <td className="is-text text-content-secondary">{t(`analysis.states.${entry.state}`)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

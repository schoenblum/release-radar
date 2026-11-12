import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import type { AnalysisReleases, AnalysisStanding } from "../../api/types";
import ErrorNotice from "../../components/ErrorNotice";
import { PageLoading } from "../../components/Spinner";
import { AnalysisHeader } from "./AnalysisLayout";
import { cardLabel, formatValue, type Language } from "./labels";
import { recordLink } from "./RankingTable";
import { pagePath, RELEASE_PARAM } from "./state";
import { useReleases } from "./useAnalysis";

/**
 * Analysis → All releases (Daniel, 2026-11-12): every shown release by title and date, on the
 * score and the three numbers that travel, each against the median of the analysed releases.
 * The title opens the record; a number opens its measure's page with the release picked out.
 */
type Column = AnalysisReleases["columns"][number];
type Line = AnalysisReleases["releases"][number];
type Sort = { by: string; desc: boolean };

const RELEASE = "release";
const NEWEST: Sort = { by: RELEASE, desc: true };
// Beyond twice the median, a bar is full: the per cent says how far.
const FULL = 100;

function percent(difference: number): string {
  const rounded = Math.round(difference);
  if (rounded === 0) return "±0%";
  return `${rounded > 0 ? "+" : "−"}${Math.abs(rounded).toLocaleString("en-US")}%`;
}

function Standing({
  standing,
  column,
  to,
  title,
}: {
  standing: AnalysisStanding | undefined;
  column: Column;
  to: string;
  title: string;
}) {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  if (!standing || standing.value === null) {
    const state = standing?.state ?? "not_applicable";
    return (
      <span className="text-content-secondary">
        {state === "missing" ? "–" : t(`analysis.states.${state}`)}
      </span>
    );
  }
  const difference = standing.difference;
  const width = difference === null ? 0 : Math.min(Math.abs(difference), FULL) / 2;
  const words =
    difference === null
      ? t("analysis.releases.no_median")
      : t(difference >= 0 ? "analysis.releases.above" : "analysis.releases.below", {
          percent: Math.abs(Math.round(difference)),
        });
  return (
    <Link className="standing" to={to} title={`${title}: ${words}`}>
      <span className="standing-value">
        {formatValue(standing.value, column.decimals, language)}
        {standing.provisional && (
          <span className="grid-badge" title={t("analysis.provisional_hint")}>
            {t("analysis.provisional")}
          </span>
        )}
      </span>
      <span className="standing-track" aria-hidden="true">
        <span className="standing-middle" />
        {difference !== null && (
          <span
            className={difference >= 0 ? "standing-bar standing-above" : "standing-bar standing-below"}
            style={difference >= 0 ? { left: "50%", width: `${width}%` } : { right: "50%", width: `${width}%` }}
          />
        )}
      </span>
      <span className="standing-percent" aria-hidden="true">
        {difference === null ? "" : percent(difference)}
      </span>
      <span className="sr-only">{words}</span>
    </Link>
  );
}

export default function AllReleases() {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  const [params] = useSearchParams();
  const { data, error, isLoading } = useReleases();
  const [sort, setSort] = useState<Sort>(NEWEST);

  const ordered = useMemo(() => {
    if (!data) return [];
    const value = (line: Line): number | string | null =>
      sort.by === RELEASE ? line.release_date : (line.standings[sort.by]?.value ?? null);
    return [...data.releases].sort((a, b) => {
      const left = value(a);
      const right = value(b);
      // Lines without a value stay at the bottom, whichever way.
      if (left === null || right === null) return left === right ? 0 : left === null ? 1 : -1;
      const order = left < right ? -1 : left > right ? 1 : 0;
      return (sort.desc ? -order : order) || (a.code ?? "").localeCompare(b.code ?? "");
    });
  }, [data, sort]);

  if (isLoading) return <PageLoading />;
  if (!data) return <ErrorNotice error={error} />;
  const { scope, columns } = data;
  const nameOf = (column: Column) => cardLabel(column, language, scope.profile);

  function choose(by: string): void {
    // Numbers read best highest first; releases newest first.
    setSort((current) => (current.by === by ? { by, desc: !current.desc } : { by, desc: true }));
  }

  function heading(by: string, name: string) {
    const active = sort.by === by;
    return (
      <button type="button" className="sort-button" onClick={() => choose(by)}>
        {name}
        <span aria-hidden="true">{active ? (sort.desc ? " ▼" : " ▲") : ""}</span>
      </button>
    );
  }

  function measurePath(key: string, releaseId: string): string {
    const path = pagePath(key, params);
    const picked = new URLSearchParams({ [RELEASE_PARAM]: releaseId }).toString();
    return `${path}${path.includes("?") ? "&" : "?"}${picked}`;
  }

  return (
    <div>
      <AnalysisHeader
        title={t("analysis.releases.title")}
        intro={t("analysis.releases.intro")}
        scope={scope}
      />
      <ErrorNotice error={error} />
      {ordered.length === 0 ? (
        <p className="text-content-secondary">{t("analysis.releases.none")}</p>
      ) : (
        <div className="table-scroll">
          <table className="count-table rank-table releases-table">
            <caption className="sr-only">{t("analysis.releases.caption")}</caption>
            <thead>
              <tr>
                <th
                  scope="col"
                  className="is-text"
                  aria-sort={sort.by === RELEASE ? (sort.desc ? "descending" : "ascending") : undefined}
                >
                  {heading(RELEASE, t("analysis.releases.release"))}
                </th>
                {columns.map((column) => (
                  <th
                    key={column.key}
                    scope="col"
                    className="is-text"
                    aria-sort={
                      sort.by === column.key ? (sort.desc ? "descending" : "ascending") : undefined
                    }
                  >
                    {heading(column.key, nameOf(column))}
                    <span className="block text-xs font-normal text-content-secondary">
                      {column.median === null
                        ? t("analysis.releases.no_values")
                        : t("analysis.releases.median", {
                            median: formatValue(column.median, column.decimals, language),
                          })}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ordered.map((line) => (
                <tr key={line.id}>
                  <th scope="row" className="is-text analysis-title-cell">
                    <Link to={recordLink(line.id)}>{line.title || t("data.no_title")}</Link>
                    <span className="block text-xs font-normal text-content-secondary">
                      {[line.code, line.release_date].filter(Boolean).join(" · ")}
                    </span>
                  </th>
                  {columns.map((column) => (
                    <td key={column.key} className="is-text">
                      <Standing
                        standing={line.standings[column.key]}
                        column={column}
                        to={measurePath(column.key, line.id)}
                        title={nameOf(column)}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-4xs max-w-3xl text-sm text-content-secondary">
        {t("analysis.releases.how")}
      </p>
    </div>
  );
}

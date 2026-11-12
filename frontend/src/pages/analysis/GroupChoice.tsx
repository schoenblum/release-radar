import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import type { AnalysisOptions, AnalysisScope, FilterDimension } from "../../api/types";
import { useOptions } from "./AnalysisLayout";
import { optionsOf } from "./labels";
import { groupIn, withGroup } from "./state";

/** Every grouping, in the order the choice lists them. Never the writer (D9). */
export const GROUPINGS: FilterDimension[] = ["ay", "type", "field", "unit", "emb", "gender"];
/** A survey chart is split by any but the unit: some twenty units would make twenty bars per
 * box (the server's ANSWER_GROUPINGS). A measure's page splits by unit as rows instead. */
export const ANSWER_GROUPINGS = GROUPINGS.filter((grouping) => grouping !== "unit");

/**
 * The groupings worth offering: those with two values or more among the analysed releases.
 * With only peer-reviewed publications analysed, a split by type would be one group.
 */
export function usefulGroupings(
  offered: FilterDimension[],
  options: AnalysisOptions,
  scope: AnalysisScope,
): FilterDimension[] {
  return offered.filter((dimension) => {
    const analysed = scope.analysed[dimension];
    const values = analysed ?? optionsOf(options, dimension).map((option) => option.value);
    return values.length >= 2;
  });
}

/**
 * "Compare by": what a chart is split by (Daniel, 2026-11-12), kept in the address under
 * `param` so the view can be bookmarked.
 */
export default function GroupChoice({
  param,
  scope,
  offered = GROUPINGS,
  label,
}: {
  param: string;
  scope: AnalysisScope;
  offered?: FilterDimension[];
  /** For a screen reader, when several charts on a page each have one. */
  label?: string;
}) {
  const { t } = useTranslation();
  const options = useOptions();
  const [params, setParams] = useSearchParams();
  // A split this chart does not offer (the unit, carried over from a measure) is none here.
  const asked = groupIn(params, param);
  const current = asked && offered.includes(asked) ? asked : null;
  const useful = usefulGroupings(offered, options, scope);
  // A choice from a bookmark stays visible, even if it splits nothing now.
  const choices = current && !useful.includes(current) ? [...useful, current] : useful;
  if (choices.length === 0) return null;
  return (
    <label className="flex items-center gap-5xs text-sm">
      <span>{t("analysis.group.label")}</span>
      <select
        className="filter-select"
        aria-label={label}
        value={current ?? ""}
        onChange={(event) =>
          setParams((now) =>
            withGroup(now, param, (event.target.value || null) as FilterDimension | null),
          )
        }
      >
        <option value="">{t("analysis.group.none")}</option>
        {choices.map((dimension) => (
          <option key={dimension} value={dimension}>
            {t(`analysis.group.options.${dimension}`)}
          </option>
        ))}
      </select>
    </label>
  );
}

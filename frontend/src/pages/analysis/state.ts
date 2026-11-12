import type { AnalysisFilterState, FilterDimension } from "../../api/types";

/**
 * The Analysis pages keep both filters, the profile and the Altmetric basis in the address
 * (phase-2 brief §5.1), so a view can be bookmarked and every Analysis link carries it over.
 * `a_<dimension>` is *analysed*, `s_<dimension>` *shown*: a comma-separated list, `all` for every
 * value, absent for the institution's default. The server reads the same names.
 */
export const DIMENSIONS: FilterDimension[] = ["type", "ay", "unit", "field", "emb", "gender"];
export type FilterSide = "a" | "s";
export const PROFILE_PARAM = "profile";
export const ALTMETRIC_PARAM = "altmetric";
/** A release picked out on a measure's page, as from All releases. Never sent to the server. */
export const RELEASE_PARAM = "release";
/**
 * What a measure's chart is split by (Daniel, 2026-11-12): one of the filter dimensions. It
 * carries over between measures, so years compare on each in turn.
 */
export const GROUP_PARAM = "group";
export const ALL = "all";

const CARRIED = new Set([
  ...DIMENSIONS.flatMap((dimension) => [`a_${dimension}`, `s_${dimension}`]),
  PROFILE_PARAM,
  ALTMETRIC_PARAM,
  GROUP_PARAM,
]);

/** A survey question's own page. */
export function answersPath(question: string, params: URLSearchParams): string {
  return `/analysis/answers/${encodeURIComponent(question)}${queryOf(params)}`;
}

/** A grouping from the address, if it names one. */
export function groupIn(params: URLSearchParams, name: string): FilterDimension | null {
  const value = params.get(name);
  return value && (DIMENSIONS as string[]).includes(value) ? (value as FilterDimension) : null;
}

/** The address with a grouping chosen, or taken away. */
export function withGroup(
  params: URLSearchParams,
  name: string,
  value: FilterDimension | null,
): URLSearchParams {
  const next = new URLSearchParams(params);
  if (value) next.set(name, value);
  else next.delete(name);
  return next;
}

export function paramName(side: FilterSide, dimension: FilterDimension): string {
  return `${side}_${dimension}`;
}

/** The part of the address that belongs to Analysis, in a fixed order so equal views share a
 * cache entry. Anything else (a page's own sort, say) stays behind. */
export function carried(params: URLSearchParams): URLSearchParams {
  const found = new URLSearchParams();
  [...CARRIED].forEach((name) => {
    const value = params.get(name);
    if (value !== null) found.set(name, value);
  });
  return found;
}

/** A query string for the API or a link: "" or "?…". */
export function queryOf(params: URLSearchParams, extra: Record<string, string> = {}): string {
  const found = carried(params);
  Object.entries(extra).forEach(([name, value]) => found.set(name, value));
  const text = found.toString();
  return text ? `?${text}` : "";
}

/**
 * The address after choosing values for one dimension. `null` means every value. Choosing the
 * institution's default writes nothing, so the address stays short.
 */
export function withChoice(
  params: URLSearchParams,
  side: FilterSide,
  dimension: FilterDimension,
  values: string[] | null,
  defaults: AnalysisFilterState,
): URLSearchParams {
  const next = new URLSearchParams(params);
  const name = paramName(side, dimension);
  const fallback = defaults[dimension];
  if (sameChoice(values, fallback)) next.delete(name);
  else next.set(name, values === null ? ALL : [...values].sort().join(","));
  return next;
}

export function sameChoice(left: string[] | null, right: string[] | null): boolean {
  if (left === null || right === null) return left === right;
  if (left.length !== right.length) return false;
  const others = new Set(right);
  return left.every((value) => others.has(value));
}

/** Back to the institution's defaults for both filters; the profile and basis stay. */
export function withoutFilters(params: URLSearchParams): URLSearchParams {
  const next = new URLSearchParams(params);
  DIMENSIONS.forEach((dimension) => {
    next.delete(paramName("a", dimension));
    next.delete(paramName("s", dimension));
  });
  return next;
}

export function hasFilters(params: URLSearchParams): boolean {
  return DIMENSIONS.some(
    (dimension) => params.has(paramName("a", dimension)) || params.has(paramName("s", dimension)),
  );
}

/**
 * The shown filter after a change to the analysed one: whatever analysed no longer includes
 * leaves shown too, as the server would do anyway (shown lies within analysed).
 */
export function narrowShown(
  params: URLSearchParams,
  dimension: FilterDimension,
  analysed: string[] | null,
): URLSearchParams {
  const name = paramName("s", dimension);
  const raw = params.get(name);
  if (raw === null || raw === ALL || analysed === null) return params;
  const allowed = new Set(analysed);
  const kept = raw.split(",").filter((value) => allowed.has(value));
  const next = new URLSearchParams(params);
  if (kept.length) next.set(name, kept.join(","));
  else next.delete(name);
  return next;
}

/** Dimension keys hold dots (`ea_views.d28`), which the address keeps as they are. */
export function pagePath(key: string, params: URLSearchParams): string {
  return `/analysis/d/${encodeURIComponent(key)}${queryOf(params)}`;
}

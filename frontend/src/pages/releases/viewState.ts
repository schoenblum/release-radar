import type { Release, ReleaseFilters } from "../../api/types";
import type { GridColumn, SortState } from "./columns";

/**
 * What a view shows lives in the address, so it can be bookmarked and shared (R7.6.1).
 * Short names there, the API's names everywhere else.
 */
const IN_ADDRESS = {
  academic_year: "ay",
  field_id: "field",
  unit_id: "unit",
  researcher_id: "researcher",
  writer_id: "writer",
  q: "q",
} as const satisfies Record<keyof ReleaseFilters, string>;

type FilterKey = keyof typeof IN_ADDRESS;
export const FILTER_KEYS = Object.keys(IN_ADDRESS) as FilterKey[];
export const SORT_PARAM = "sort";

export function filtersFrom(params: URLSearchParams): ReleaseFilters {
  const filters: ReleaseFilters = {};
  for (const key of FILTER_KEYS) {
    const raw = params.get(IN_ADDRESS[key])?.trim();
    if (!raw) continue;
    if (key === "academic_year") {
      const year = Number(raw);
      if (Number.isInteger(year) && year >= 1900 && year <= 2999) filters.academic_year = year;
    } else {
      filters[key] = raw;
    }
  }
  return filters;
}

/** Change one filter in the address, leaving everything else as it is. */
export function withFilter(
  params: URLSearchParams,
  key: FilterKey,
  value: string | number | null | undefined,
): URLSearchParams {
  const next = new URLSearchParams(params);
  const text = value === null || value === undefined ? "" : String(value).trim();
  if (text) next.set(IN_ADDRESS[key], text);
  else next.delete(IN_ADDRESS[key]);
  return next;
}

export function withoutFilters(params: URLSearchParams): URLSearchParams {
  const next = new URLSearchParams(params);
  FILTER_KEYS.forEach((key) => next.delete(IN_ADDRESS[key]));
  return next;
}

export function hasFilters(filters: ReleaseFilters): boolean {
  return FILTER_KEYS.some((key) => filters[key] !== undefined);
}

/** The query string for ``GET /releases``, in a fixed order so equal views share a cache. */
export function filterQuery(filters: ReleaseFilters): string {
  const query = new URLSearchParams();
  for (const key of FILTER_KEYS) {
    const value = filters[key];
    if (value !== undefined) query.set(key, String(value));
  }
  return query.toString();
}

export function sortFrom(params: URLSearchParams): SortState | null {
  const raw = params.get(SORT_PARAM);
  if (!raw) return null;
  return raw.startsWith("-") ? { column: raw.slice(1), desc: true } : { column: raw, desc: false };
}

export function sortText(sort: SortState | null): string | null {
  if (!sort) return null;
  return sort.desc ? `-${sort.column}` : sort.column;
}

/** Clicking a header: ascending, then descending, then back to newest first. */
export function nextSort(current: SortState | null, column: string): SortState | null {
  if (current?.column !== column) return { column, desc: false };
  return current.desc ? null : { column, desc: true };
}

/** Empty values go last whichever way round, as in a spreadsheet. */
export function compareBy(
  column: GridColumn,
  desc: boolean,
  language: string,
): (a: Release, b: Release) => number {
  const collator = new Intl.Collator(language, { numeric: true, sensitivity: "base" });
  return (a, b) => {
    const left = column.sortValue(a);
    const right = column.sortValue(b);
    if (left === null || right === null) {
      return left === right ? 0 : left === null ? 1 : -1;
    }
    const order =
      typeof left === "number" && typeof right === "number"
        ? left - right
        : collator.compare(String(left), String(right));
    return desc ? -order : order;
  };
}

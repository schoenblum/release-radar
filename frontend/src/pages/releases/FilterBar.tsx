import { useQuery } from "@tanstack/react-query";
import { useEffect, useState, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

import { http } from "../../api/client";
import type { ReleaseFilters, Researcher, ResearcherPage } from "../../api/types";
import RecordSummary from "../../components/RecordSummary";
import { academicYearLabel } from "../../dates";
import type { GridContext } from "./columns";
import { hasFilters } from "./viewState";

type Key = keyof ReleaseFilters;

const SEARCH_DELAY_MS = 300;

/** Typing searches after a short pause, so the address and the list keep up without lag. */
function SearchBox({ value, onChange }: { value: string; onChange: (text: string) => void }) {
  const { t } = useTranslation();
  const [text, setText] = useState(value);
  useEffect(() => {
    if (text === value) return;
    const timer = setTimeout(() => onChange(text), SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
    // Only typing starts a search, not the address catching up with it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text]);
  return (
    <input
      type="search"
      className="filter-search"
      aria-label={t("data.filters.search")}
      placeholder={t("data.filters.search_placeholder")}
      value={text}
      onChange={(event) => setText(event.target.value)}
      onKeyDown={(event) => {
        // Enter searches straight away.
        if (event.key === "Enter" && !event.nativeEvent.isComposing) onChange(text);
      }}
    />
  );
}

/** Names are not unique (R6.3.1), so the choice shows what tells namesakes apart. */
function ResearcherFilter({
  value,
  context,
  onChange,
}: {
  value: string | undefined;
  context: GridContext;
  onChange: (id: string | null) => void;
}) {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [cursor, setCursor] = useState(0);
  const term = query.trim();

  const { data: chosen } = useQuery({
    queryKey: ["researchers", "one", value],
    queryFn: () => http.get<Researcher>(`/researchers/${value}`),
    enabled: !!value,
  });
  const { data: found } = useQuery({
    queryKey: ["researchers", "picker", term],
    queryFn: () =>
      http.get<ResearcherPage>(`/researchers?limit=8&search=${encodeURIComponent(term)}`),
    enabled: open && term.length > 0,
  });
  const choices = term.length > 0 ? (found?.items ?? []) : [];
  const active = Math.min(cursor, Math.max(choices.length - 1, 0));

  function pick(record: Researcher): void {
    onChange(record.id);
    setQuery("");
    setOpen(false);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>): void {
    if (event.nativeEvent.isComposing) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setCursor(Math.min(active + 1, choices.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setCursor(Math.max(active - 1, 0));
    } else if (event.key === "Enter" && choices[active]) {
      event.preventDefault();
      pick(choices[active]);
    } else if (event.key === "Escape") {
      setQuery("");
      setOpen(false);
    }
  }

  if (value) {
    return (
      <span className="filter-chip">
        <span className="truncate">
          {t("data.filters.researcher")}: {chosen?.name ?? "…"}
        </span>
        <button
          type="button"
          className="filter-chip-clear"
          aria-label={t("data.filters.clear_one", { name: chosen?.name ?? "" })}
          onClick={() => onChange(null)}
        >
          ×
        </button>
      </span>
    );
  }
  return (
    <div className="relative">
      <input
        className="filter-search filter-researcher"
        role="combobox"
        aria-expanded={open && choices.length > 0}
        aria-label={t("data.filters.researcher")}
        placeholder={t("data.filters.researcher_placeholder")}
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setCursor(0);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={onKeyDown}
      />
      {open && choices.length > 0 && (
        <ul role="listbox" aria-label={t("data.filters.researcher")} className="picker-list">
          {choices.map((record, index) => (
            <li key={record.id} role="presentation">
              <button
                type="button"
                role="option"
                aria-selected={index === active}
                tabIndex={-1}
                className={index === active ? "picker-option is-active" : "picker-option"}
                // Before the input loses focus, which closes the list.
                onMouseDown={(event) => {
                  event.preventDefault();
                  pick(record);
                }}
              >
                <RecordSummary record={record} units={context.units} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Choose({
  label,
  anyLabel,
  value,
  options,
  onChange,
}: {
  label: string;
  anyLabel: string;
  value: string | number | undefined;
  options: { value: string; label: string }[];
  onChange: (value: string | null) => void;
}) {
  const current = value === undefined ? "" : String(value);
  return (
    <select
      aria-label={label}
      className={current ? "filter-select is-set" : "filter-select"}
      value={current}
      onChange={(event) => onChange(event.target.value || null)}
    >
      <option value="">{anyLabel}</option>
      {/* A value from a bookmark that is no longer offered still shows what it is. */}
      {current && !options.some((option) => option.value === current) && (
        <option value={current}>{current}</option>
      )}
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

/**
 * Narrows the view (R7.6.1): year, field, type, unit, researcher, writer, and words anywhere.
 * Each choice is one click and goes into the address, so a view can be bookmarked. Every type
 * shows by default: data entry needs them all, whatever analysis leaves out.
 */
export default function FilterBar({
  filters,
  years,
  showWriter,
  context,
  onChange,
  onClear,
}: {
  filters: ReleaseFilters;
  years: number[];
  showWriter: boolean;
  context: GridContext;
  onChange: (key: Key, value: string | number | null) => void;
  onClear: () => void;
}) {
  const { t, i18n } = useTranslation();
  const isJa = i18n.language === "ja";
  const named = (en: string, ja: string | null) => (isJa && ja) || en;
  // Searching again after Clear starts from an empty box.
  const [searchKey, setSearchKey] = useState(0);

  // A retired entry stays in the list only while it is chosen.
  const offered = <T extends { id: string; is_active: boolean }>(rows: T[], chosen?: string) =>
    rows.filter((row) => row.is_active || row.id === chosen);
  // An institution that hides the type in Settings has no use for its filter either.
  const showType = context.coreFields.some((row) => row.key === "release_type" && !row.hidden);

  return (
    <div className="filter-bar" role="search" aria-label={t("data.filters.label")}>
      <SearchBox
        key={searchKey}
        value={filters.q ?? ""}
        onChange={(text) => onChange("q", text.trim() ? text : null)}
      />
      <Choose
        label={t("data.filters.year")}
        anyLabel={t("data.filters.any_year")}
        value={filters.academic_year}
        options={years.map((year) => ({
          value: String(year),
          label: academicYearLabel(year, i18n.language),
        }))}
        onChange={(value) => onChange("academic_year", value === null ? null : Number(value))}
      />
      <Choose
        label={t("data.filters.field")}
        anyLabel={t("data.filters.any_field")}
        value={filters.field_id}
        options={offered(context.fields, filters.field_id).map((row) => ({
          value: row.id,
          label: named(row.name_en, row.name_ja),
        }))}
        onChange={(value) => onChange("field_id", value)}
      />
      {showType && (
        <Choose
          label={t("data.filters.release_type")}
          anyLabel={t("data.filters.any_release_type")}
          value={filters.release_type_id}
          options={[
            ...offered(context.releaseTypes, filters.release_type_id).map((row) => ({
              value: row.id,
              label: named(row.name_en, row.name_ja),
            })),
            { value: "none", label: t("data.filters.no_release_type") },
          ]}
          onChange={(value) => onChange("release_type_id", value)}
        />
      )}
      <Choose
        label={t("data.filters.unit")}
        anyLabel={t("data.filters.any_unit")}
        value={filters.unit_id}
        options={offered(context.units, filters.unit_id).map((row) => ({
          value: row.id,
          label: named(row.name_en, row.name_ja),
        }))}
        onChange={(value) => onChange("unit_id", value)}
      />
      {showWriter && (
        <Choose
          label={t("data.filters.writer")}
          anyLabel={t("data.filters.any_writer")}
          value={filters.writer_id}
          options={[
            ...context.writers.map((row) => ({
              value: row.id,
              label: named(row.display_name_en, row.display_name_ja),
            })),
            // Releases still waiting for one, such as an import's unknown names.
            { value: "none", label: t("data.filters.no_writer") },
          ]}
          onChange={(value) => onChange("writer_id", value)}
        />
      )}
      <ResearcherFilter
        value={filters.researcher_id}
        context={context}
        onChange={(value) => onChange("researcher_id", value)}
      />
      {hasFilters(filters) && (
        <button
          type="button"
          className="btn-small"
          onClick={() => {
            setSearchKey((key) => key + 1);
            onClear();
          }}
        >
          {t("data.filters.clear")}
        </button>
      )}
    </div>
  );
}

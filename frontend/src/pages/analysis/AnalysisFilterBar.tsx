import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import type {
  AnalysisFilterState,
  AnalysisOptions,
  AnalysisScope,
  FilterDimension,
} from "../../api/types";
import { optionLabel, optionsOf, scopeSentence, type Language } from "./labels";
import {
  DIMENSIONS,
  hasFilters,
  narrowShown,
  type FilterSide,
  withChoice,
  withoutFilters,
} from "./state";

/** The values after a click on one: from "all" it picks that one; else it toggles it. */
export function toggled(current: string[] | null, value: string): string[] | null {
  if (current === null) return [value];
  if (current.includes(value)) {
    const rest = current.filter((item) => item !== value);
    return rest.length ? rest : null;
  }
  return [...current, value];
}

function Picker({
  side,
  dimension,
  options,
  current,
  within,
  onChoose,
}: {
  side: FilterSide;
  dimension: FilterDimension;
  options: AnalysisOptions;
  current: string[] | null;
  /** For *shown*: only what *analysed* includes. */
  within: string[] | null;
  onChoose: (values: string[] | null) => void;
}) {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const offered = optionsOf(options, dimension).filter(
    (option) => within === null || within.includes(option.value),
  );

  useEffect(() => {
    if (!open) return;
    const close = (event: PointerEvent): void => {
      if (!box.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);

  const name = t(`analysis.filters.dimensions.${dimension}`);
  const labelOf = (value: string): string =>
    optionLabel(
      t,
      language,
      dimension,
      offered.find((option) => option.value === value) ?? { value, label_en: null, label_ja: null },
    );
  const summary =
    current === null
      ? t("analysis.filters.all")
      : current.length === 1
        ? labelOf(current[0])
        : t("analysis.filters.chosen", { count: current.length });
  const restricted = current !== null;

  if (offered.length === 0) return null;
  return (
    <div
      ref={box}
      className="relative"
      onKeyDown={(event) => {
        if (event.key === "Escape") setOpen(false);
      }}
    >
      <button
        type="button"
        className={restricted ? "filter-button filter-button-on" : "filter-button"}
        aria-expanded={open}
        aria-label={t("analysis.filters.picker_label", {
          side: t(`analysis.filters.${side === "a" ? "analysed" : "shown"}`),
          name,
          summary,
        })}
        onClick={() => setOpen((now) => !now)}
      >
        <span className="text-content-secondary">{name}:</span>{" "}
        <span className="max-w-[12rem] truncate">{summary}</span>
        <span aria-hidden="true"> ▾</span>
      </button>
      {open && (
        <div className="popover popover-left" role="group" aria-label={name}>
          <div className="flex flex-wrap gap-5xs">
            <button
              type="button"
              className="choice-chip"
              aria-pressed={current === null}
              onClick={() => onChoose(null)}
            >
              {t("analysis.filters.all")}
            </button>
            {offered.map((option) => (
              <button
                key={option.value}
                type="button"
                className="choice-chip"
                aria-pressed={current !== null && current.includes(option.value)}
                onClick={() => onChoose(toggled(current, option.value))}
              >
                {optionLabel(t, language, dimension, option)}
                <span className="choice-count"> {option.count}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * The two filters, on every Analysis page (phase-2 brief §5.1): *analysed* decides what every
 * number is computed from, *shown* only which of those releases appear. Both live in the
 * address and carry over between pages.
 */
export default function AnalysisFilterBar({
  options,
  scope,
}: {
  options: AnalysisOptions;
  scope: AnalysisScope;
}) {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  const [params, setParams] = useSearchParams();

  function choose(side: FilterSide, dimension: FilterDimension, values: string[] | null): void {
    setParams((current) => {
      const defaults: AnalysisFilterState = options.defaults[side === "a" ? "analysed" : "shown"];
      let next = withChoice(current, side, dimension, values, defaults);
      if (side === "a") next = narrowShown(next, dimension, values);
      return next;
    });
  }

  const rows: { side: FilterSide; filter: AnalysisFilterState }[] = [
    { side: "a", filter: scope.analysed },
    { side: "s", filter: scope.shown },
  ];

  return (
    <div className="analysis-filters" role="search" aria-label={t("analysis.filters.label")}>
      {rows.map(({ side, filter }) => (
        <div key={side} className="analysis-filter-row">
          <span className="analysis-filter-side">
            {t(`analysis.filters.${side === "a" ? "analysed" : "shown"}`)}
          </span>
          {DIMENSIONS.map((dimension) => (
            <Picker
              key={dimension}
              side={side}
              dimension={dimension}
              options={options}
              current={filter[dimension]}
              within={side === "s" ? scope.analysed[dimension] : null}
              onChoose={(values) => choose(side, dimension, values)}
            />
          ))}
        </div>
      ))}
      <div className="flex flex-wrap items-baseline gap-x-4xs gap-y-5xs">
        <p className="analysis-sentence" aria-live="polite">
          {scopeSentence(t, language, options, scope)}
        </p>
        {hasFilters(params) && (
          <button
            type="button"
            className="btn-small"
            onClick={() => setParams((current) => withoutFilters(current))}
          >
            {t("analysis.filters.reset")}
          </button>
        )}
      </div>
    </div>
  );
}

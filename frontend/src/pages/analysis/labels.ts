import type { TFunction } from "i18next";

import type {
  AnalysisCard,
  AnalysisFilterState,
  AnalysisOption,
  AnalysisOptions,
  AnalysisProfile,
  AnalysisScope,
  FilterDimension,
} from "../../api/types";
import { academicYearLabel } from "../../dates";
import { DIMENSIONS, sameChoice } from "./state";

export type Language = "en" | "ja";

/** i18next reads dots as nesting, and dimension keys hold dots (`ea_views.d28`). */
export function textKey(key: string): string {
  return key.replaceAll(".", "_");
}

export function named(language: Language, en: string | null, ja: string | null): string {
  return (language === "ja" && ja) || en || "";
}

export function profileName(profile: AnalysisProfile, language: Language): string {
  return named(language, profile.name_en, profile.name_ja);
}

export function optionsOf(options: AnalysisOptions, dimension: FilterDimension): AnalysisOption[] {
  switch (dimension) {
    case "type":
      return options.release_types;
    case "ay":
      return options.academic_years;
    case "unit":
      return options.units;
    case "field":
      return options.fields;
    case "emb":
      return options.embargoed;
    case "gender":
      return options.genders;
  }
}

const GENDERS = ["F", "M", "other", "not_recorded"] as const;
type Gender = (typeof GENDERS)[number];

function isGender(value: string): value is Gender {
  return (GENDERS as readonly string[]).includes(value);
}

/** What one value of a filter is called on screen. */
export function optionLabel(
  t: TFunction,
  language: Language,
  dimension: FilterDimension,
  option: Pick<AnalysisOption, "value" | "label_en" | "label_ja">,
): string {
  if (dimension === "ay") return academicYearLabel(Number(option.value), language);
  if (dimension === "emb") {
    return t(option.value === "1" ? "analysis.filters.emb_yes" : "analysis.filters.emb_no");
  }
  if (dimension === "gender") {
    return isGender(option.value) ? t(`analysis.filters.genders.${option.value}`) : option.value;
  }
  if (option.value === "none") return t(`analysis.filters.none.${dimension}`);
  return named(language, option.label_en, option.label_ja) || option.value;
}

export function valueLabel(
  t: TFunction,
  language: Language,
  options: AnalysisOptions,
  dimension: FilterDimension,
  value: string,
): string {
  const found = optionsOf(options, dimension).find((option) => option.value === value);
  return optionLabel(t, language, dimension, found ?? { value, label_en: null, label_ja: null });
}

/** "Peer-reviewed publication; Graduate School of Science": what a filter restricts. */
export function restrictions(
  t: TFunction,
  language: Language,
  options: AnalysisOptions,
  filter: AnalysisFilterState,
  compared?: AnalysisFilterState,
): string[] {
  const separator = t("analysis.sentence.separator");
  return DIMENSIONS.flatMap((dimension) => {
    const values = filter[dimension];
    if (values === null) return [];
    if (compared && sameChoice(values, compared[dimension])) return [];
    return [values.map((value) => valueLabel(t, language, options, dimension, value)).join(separator)];
  });
}

function yearsText(scope: AnalysisScope, language: Language): string | null {
  if (scope.first_year === null || scope.last_year === null) return null;
  const first = academicYearLabel(scope.first_year, language);
  if (scope.first_year === scope.last_year) return first;
  return `${first}–${academicYearLabel(scope.last_year, language)}`;
}

/**
 * The plain sentence under the filter bar, e.g. "Analysed: 108 releases (Peer-reviewed
 * publication), AY2025–AY2026. Shown: 23 of them (Graduate School of Science)."
 */
export function scopeSentence(
  t: TFunction,
  language: Language,
  options: AnalysisOptions,
  scope: AnalysisScope,
): string {
  const joiner = t("analysis.sentence.joiner");
  const analysedParts = restrictions(t, language, options, scope.analysed);
  const years = yearsText(scope, language);
  const analysed = t("analysis.sentence.analysed", {
    count: scope.analysed_count,
    filters: analysedParts.length ? t("analysis.sentence.within", { text: analysedParts.join(joiner) }) : "",
    years: years ? t("analysis.sentence.years", { years }) : "",
  });
  const shownParts = restrictions(t, language, options, scope.shown, scope.analysed);
  const shown =
    scope.shown_count === scope.analysed_count && !shownParts.length
      ? t("analysis.sentence.shown_all")
      : t("analysis.sentence.shown", {
          count: scope.shown_count,
          filters: shownParts.length ? t("analysis.sentence.within", { text: shownParts.join(joiner) }) : "",
        });
  return t("analysis.sentence.full", { analysed, shown });
}

export function formatValue(value: number, decimals: number, language: Language): string {
  return value.toLocaleString(language === "ja" ? "ja-JP" : "en-US", {
    maximumFractionDigits: decimals,
    minimumFractionDigits: 0,
  });
}

/** A card's name: the profile's for the score, else the dimension's. */
export function cardLabel(
  card: Pick<AnalysisCard, "key" | "label_en" | "label_ja">,
  language: Language,
  profile: AnalysisProfile | null,
): string {
  if (card.key === "score" && profile) return profileName(profile, language);
  return named(language, card.label_en, card.label_ja);
}

/** One line on what a dimension measures; nothing for one the app does not know yet. */
export function cardDescription(t: TFunction, key: string, profile: AnalysisProfile | null): string {
  if (key === "score" && profile) {
    return t("analysis.describe.score", { version: profile.version });
  }
  return t(`analysis.describe.${textKey(key)}`, { defaultValue: "" });
}

/** The plain caption under a card's chart (phase-2 brief §5.2). */
export function caption(
  t: TFunction,
  language: Language,
  card: AnalysisCard,
  sameSet: boolean,
  logScale: boolean,
): string {
  const box = card.box;
  if (!box) return t("analysis.card.no_values");
  const show = (value: number): string => formatValue(value, card.decimals, language);
  const parts: string[] = [];
  if (box.n < 4) {
    parts.push(t("analysis.card.few", { count: box.n, median: show(box.median) }));
  } else {
    parts.push(t("analysis.card.half", { low: show(box.q1), high: show(box.q3) }));
  }
  if (sameSet) {
    if (box.n >= 4) parts.push(t("analysis.card.median_same", { median: show(box.median) }));
  } else if (card.shown_median === null) {
    parts.push(t("analysis.card.none_shown"));
  } else {
    parts.push(
      t("analysis.card.shown_median", {
        count: card.points.length,
        median: show(card.shown_median),
      }),
    );
  }
  if (logScale) parts.push(t("analysis.card.log_on"));
  return parts.join(" ");
}

/** "94 with a value, 12 missing, 2 not applicable": missing data stays visible (P3). */
export function countLine(t: TFunction, card: AnalysisCard): string {
  const counts = card.counts;
  const parts =
    card.key === "score"
      ? [
          t("analysis.counts.scored", { count: counts.value }),
          t("analysis.counts.insufficient", { count: counts.insufficient }),
          ...(counts.provisional ? [t("analysis.counts.provisional", { count: counts.provisional })] : []),
        ]
      : [
          t("analysis.counts.value", { count: counts.value }),
          t("analysis.counts.missing", { count: counts.missing }),
          t("analysis.counts.not_applicable", { count: counts.not_applicable }),
          ...(counts.not_yet_due ? [t("analysis.counts.not_yet_due", { count: counts.not_yet_due })] : []),
        ];
  return parts.join(t("analysis.sentence.separator"));
}

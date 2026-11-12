import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, Outlet, useOutletContext, useSearchParams } from "react-router-dom";

import type { AnalysisOptions, AnalysisScope } from "../../api/types";
import ErrorNotice from "../../components/ErrorNotice";
import { PageLoading } from "../../components/Spinner";
import AnalysisFilterBar from "./AnalysisFilterBar";
import { named, profileName, textKey, type Language } from "./labels";
import { answersPath, PROFILE_PARAM, pagePath, queryOf } from "./state";
import { useAnalysisOptions } from "./useAnalysis";

export function useOptions(): AnalysisOptions {
  return useOutletContext<AnalysisOptions>();
}

function ProfileChoice({ options, scope }: { options: AnalysisOptions; scope: AnalysisScope }) {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  const [, setParams] = useSearchParams();
  if (options.profiles.length < 2 || !scope.profile) return null;
  return (
    <label className="flex items-center gap-5xs text-sm">
      <span>{t("analysis.profile")}</span>
      <select
        className="filter-select"
        value={scope.profile.id}
        onChange={(event) => {
          const chosen = options.profiles.find((profile) => profile.id === event.target.value);
          setParams((current) => {
            const next = new URLSearchParams(current);
            if (!chosen || chosen.is_default) next.delete(PROFILE_PARAM);
            else next.set(PROFILE_PARAM, chosen.id);
            return next;
          });
        }}
      >
        {options.profiles.map((profile) => (
          <option key={profile.id} value={profile.id}>
            {profileName(profile, language)}
            {profile.is_default ? ` (${t("analysis.default_profile")})` : ""}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Heading, actions and the two filters, the same on every Analysis page. */
export function AnalysisHeader({
  title,
  intro,
  scope,
  actions,
}: {
  title: string;
  intro?: string;
  scope: AnalysisScope;
  actions?: ReactNode;
}) {
  const options = useOptions();
  return (
    <>
      <div className="mb-4xs flex flex-wrap items-center justify-between gap-4xs">
        <h1 className="text-3xl">{title}</h1>
        <div className="flex flex-wrap items-center gap-4xs">
          <ProfileChoice options={options} scope={scope} />
          {actions}
        </div>
      </div>
      {intro && <p className="mb-3xs max-w-3xl text-content-secondary">{intro}</p>}
      <AnalysisFilterBar options={options} scope={scope} />
    </>
  );
}

/**
 * The Analysis area (D30, phase-2 brief §5), for every signed-in role: the overview, all
 * releases, a page per dimension, a page per survey question and top & bottom 5, with both filters carried over between them
 * in the address.
 */
export default function AnalysisLayout() {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  const [params] = useSearchParams();
  const { data: options, error, isLoading } = useAnalysisOptions();
  if (isLoading) return <PageLoading />;
  if (!options) return <ErrorNotice error={error} />;
  const query = queryOf(params);
  const link = ({ isActive }: { isActive: boolean }): string =>
    isActive ? "analysis-tab analysis-tab-active" : "analysis-tab";

  return (
    <div>
      <nav aria-label={t("analysis.pages_label")} className="analysis-tabs">
        <NavLink end to={`/analysis${query}`} className={link}>
          {t("analysis.overview.tab")}
        </NavLink>
        <NavLink to={`/analysis/releases${query}`} className={link}>
          {t("analysis.releases.tab")}
        </NavLink>
        {options.pages.map((page) => (
          <NavLink key={page.key} to={pagePath(page.key, params)} className={link}>
            {t(`analysis.tabs.${textKey(page.key)}`, {
              defaultValue: named(language, page.label_en, page.label_ja),
            })}
          </NavLink>
        ))}
        {options.answers.map((question) => (
          <NavLink key={question} to={answersPath(question, params)} className={link}>
            {t(`analysis.answers.${question}.title`)}
          </NavLink>
        ))}
        <NavLink to={`/analysis/top${query}`} className={link}>
          {t("analysis.top.tab")}
        </NavLink>
      </nav>
      <Outlet context={options} />
    </div>
  );
}

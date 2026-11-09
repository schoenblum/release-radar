import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, Outlet } from "react-router-dom";

const SECTIONS = [
  { id: "institution" },
  { id: "users" },
  { id: "lists" },
  { id: "researchers" },
  { id: "form" },
  { id: "checkpoints" },
  { id: "score_profiles", later: true },
  { id: "survey", later: true },
  { id: "outlets", later: true },
  { id: "integrations" },
  { id: "data" },
] as const;

/** One Settings area with a section list on the left, hidden from editors and viewers. */
export default function SettingsLayout() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-s md:flex-row">
      <nav
        aria-label={t("nav.settings")}
        className="flex shrink-0 flex-wrap gap-5xs md:w-52 md:flex-col"
      >
        {SECTIONS.map((section) =>
          "later" in section ? (
            <span
              key={section.id}
              className="px-3xs py-5xs text-sm text-content-secondary opacity-60"
              title={t("common.coming_later")}
            >
              {t(`settings.sections.${section.id}`)}
            </span>
          ) : (
            <NavLink
              key={section.id}
              to={`/settings/${section.id}`}
              className={({ isActive }) => (isActive ? "nav-link nav-link-active" : "nav-link")}
            >
              {t(`settings.sections.${section.id}`)}
            </NavLink>
          ),
        )}
      </nav>
      <div className="min-w-0 flex-1">
        <Outlet />
      </div>
    </div>
  );
}

export function SectionHeader({ title, help }: { title: string; help?: string }) {
  return (
    <header className="mb-2xs max-w-3xl">
      <h1 className="text-3xl">{title}</h1>
      {help && <p className="mt-5xs text-content-secondary">{help}</p>}
    </header>
  );
}

export function SubHeading({ children }: { children: ReactNode }) {
  return <h2 className="mb-4xs mt-s text-2xl">{children}</h2>;
}

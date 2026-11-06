import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet } from "react-router-dom";

import { api } from "../api/client";
import { useAuth } from "../auth";
import { useBrand } from "../brand";
import LanguageToggle from "./LanguageToggle";
import UserMenu from "./UserMenu";
import Wordmark from "./Wordmark";

export default function Layout() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { institutionName } = useBrand();
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    staleTime: Infinity,
  });

  const items = [
    { to: "/my-releases", label: t("nav.my_releases") },
    { to: "/releases", label: t("nav.all_releases") },
    { to: "/writers", label: t("nav.writers") },
    ...(user?.role === "editor" ? [{ to: "/researchers", label: t("nav.researchers") }] : []),
    ...(user?.role === "admin" ? [{ to: "/settings", label: t("nav.settings") }] : []),
    { to: "/manual", label: t("nav.manual") },
  ];

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="skip-link">
        {t("app.skip_to_content")}
      </a>
      <header>
        <div className="flex flex-wrap items-center gap-x-xs gap-y-4xs px-xs py-3xs">
          <Link to="/" className="rounded">
            <Wordmark />
          </Link>
          <nav
            aria-label={t("nav.main")}
            className="order-last flex w-full flex-wrap gap-5xs xl:order-none xl:ml-2xs xl:w-auto xl:flex-1"
          >
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  isActive ? "nav-link nav-link-active" : "nav-link"
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-4xs">
            <LanguageToggle />
            <UserMenu />
          </div>
        </div>
        <div className="accent-rule" />
      </header>
      <main id="main" className="flex-1 px-xs py-s">
        <Outlet />
      </main>
      <footer className="px-xs py-2xs text-sm text-content-secondary">
        {institutionName}
        {institutionName && health ? " · " : ""}
        {health ? t("app.version", { version: health.version }) : ""}
      </footer>
    </div>
  );
}

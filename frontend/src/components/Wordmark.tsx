import { useTranslation } from "react-i18next";

import { useBrand } from "../brand";

function RadarGlyph() {
  return (
    <svg viewBox="0 0 32 32" className="h-7 w-7 text-content-accent" aria-hidden="true">
      <circle cx="16" cy="16" r="15" fill="currentColor" />
      <g fill="none" stroke="var(--text-on-accent)" strokeWidth="2" strokeLinecap="round">
        <path d="M16 6a10 10 0 0 1 10 10" />
        <path d="M16 11a5 5 0 0 1 5 5" />
        <path d="M16 16 8.5 8.5" />
      </g>
      <circle cx="16" cy="16" r="2.5" fill="var(--text-on-accent)" />
    </svg>
  );
}

/**
 * The institution's logo from the brand pack, or else a neutral mark, then the
 * app name. `stacked` puts the name under the logo, for narrow places.
 */
export default function Wordmark({ stacked = false }: { stacked?: boolean }) {
  const { t } = useTranslation();
  const { logoUrl, logoAlt } = useBrand();
  const name = (
    <span
      className={`whitespace-nowrap font-wordmark text-content-accent ${
        stacked ? "text-2xl" : "text-xl"
      }`}
    >
      {t("app.name")}
    </span>
  );

  if (!logoUrl) {
    return (
      <span className="flex items-center gap-3xs">
        <RadarGlyph />
        {name}
      </span>
    );
  }
  if (stacked) {
    return (
      <span className="flex flex-col items-start gap-4xs">
        <img src={logoUrl} alt={logoAlt} className="h-8 w-auto max-w-full" />
        {name}
      </span>
    );
  }
  return (
    <span className="flex flex-wrap items-center gap-x-3xs">
      <img src={logoUrl} alt={logoAlt} className="h-7 w-auto" />
      <span className="hidden h-6 w-px bg-line-disabled sm:block" aria-hidden="true" />
      {name}
    </span>
  );
}

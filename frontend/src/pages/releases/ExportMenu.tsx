import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { http } from "../../api/client";
import { errorMessage } from "../../api/errors";
import type { LandingView, ReleaseExportRequest, ReleaseFilters } from "../../api/types";

type Scope = "view" | "everything";

function Choice<T extends string>({
  name,
  legend,
  value,
  options,
  onChange,
}: {
  name: string;
  legend: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <fieldset className="mb-3xs">
      <legend className="field-label">{legend}</legend>
      {options.map((option) => (
        <label key={option.value} className="flex items-center gap-5xs py-5xs">
          <input
            type="radio"
            name={name}
            value={option.value}
            checked={value === option.value}
            onChange={() => onChange(option.value)}
          />
          {option.label}
        </label>
      ))}
    </fieldset>
  );
}

/**
 * Export (R7.6.2): what is on screen or everything, as Excel or CSV, in English or Japanese.
 * The defaults are what most people want, so it is two clicks: Export, then Download.
 */
export default function ExportMenu({
  view,
  filters,
  order,
  shown,
}: {
  view: LandingView;
  filters: ReleaseFilters;
  /** The releases in the order the grid shows them. */
  order: string[];
  shown: number;
}) {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const [scope, setScope] = useState<Scope>("view");
  const [format, setFormat] = useState<ReleaseExportRequest["format"]>("xlsx");
  // The page's language, until someone picks another.
  const [picked, setLanguage] = useState<ReleaseExportRequest["language"] | null>(null);
  const language = picked ?? (i18n.language === "ja" ? "ja" : "en");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: PointerEvent): void => {
      if (!box.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);

  async function download(): Promise<void> {
    setBusy(true);
    setError(null);
    const body: ReleaseExportRequest =
      scope === "view"
        ? { format, language, filters: { view, ...filters }, order }
        : { format, language, order: [] };
    try {
      await http.download("/releases/export", `release_radar_releases.${format}`, body);
      setOpen(false);
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

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
        className="btn-small"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        {t("data.export.button")}
      </button>
      {open && (
        <div className="popover" role="dialog" aria-label={t("data.export.title")}>
          <Choice
            name="export-scope"
            legend={t("data.export.rows")}
            value={scope}
            options={[
              { value: "view", label: t("data.export.this_view", { count: shown }) },
              { value: "everything", label: t("data.export.everything") },
            ]}
            onChange={setScope}
          />
          <Choice
            name="export-format"
            legend={t("data.export.format")}
            value={format}
            options={[
              { value: "xlsx", label: t("data.export.xlsx") },
              { value: "csv", label: t("data.export.csv") },
            ]}
            onChange={setFormat}
          />
          <Choice
            name="export-language"
            legend={t("data.export.language")}
            value={language}
            options={[
              { value: "en", label: "English" },
              { value: "ja", label: "日本語" },
            ]}
            onChange={setLanguage}
          />
          <p className="notice-info mb-3xs">{t("data.export.personal_data")}</p>
          <button
            type="button"
            className="btn-primary w-full"
            disabled={busy}
            onClick={() => void download()}
          >
            {busy ? t("data.export.preparing") : t("data.export.download")}
          </button>
          {error !== null && (
            <p role="alert" className="field-error">
              {errorMessage(t, error)}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

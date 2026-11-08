import { useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "../api/errors";

export interface ExportChoice {
  format: "xlsx" | "csv";
  language: "en" | "ja";
}

export function Choice<T extends string>({
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
 * The Export button and its panel: Excel or CSV, English or Japanese, then Download. The
 * defaults are what most people want, so it is two clicks. A page adds its own choices above.
 */
export default function ExportPopover({
  title,
  xlsxLabel,
  notice,
  download,
  children,
}: {
  title: string;
  xlsxLabel: string;
  notice: string;
  download: (choice: ExportChoice) => Promise<void>;
  children?: ReactNode;
}) {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const [format, setFormat] = useState<ExportChoice["format"]>("xlsx");
  // The page's language, until someone picks another.
  const [picked, setLanguage] = useState<ExportChoice["language"] | null>(null);
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

  async function start(): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      await download({ format, language });
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
        <div className="popover" role="dialog" aria-label={title}>
          {children}
          <Choice
            name="export-format"
            legend={t("data.export.format")}
            value={format}
            options={[
              { value: "xlsx", label: xlsxLabel },
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
          <p className="notice-info mb-3xs">{notice}</p>
          <button
            type="button"
            className="btn-primary w-full"
            disabled={busy}
            onClick={() => void start()}
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

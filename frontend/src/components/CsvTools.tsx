import type { TFunction } from "i18next";
import { useRef, useState, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";

import { http } from "../api/client";
import { codeMessage, errorMessage } from "../api/errors";
import type { ImportProblem, ImportReport } from "../api/types";

/**
 * Reads a CSV file as UTF-8, or else as Shift-JIS, which is what Japanese Excel saves
 * when asked for plain "CSV".
 */
export function decodeCsv(bytes: ArrayBuffer): string {
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    return new TextDecoder("shift_jis").decode(bytes);
  }
}

/** One problem in plain words: where it is, what was there, and what to use instead. */
export function problemMessage(t: TFunction, problem: ImportProblem): string {
  const where = { row: problem.row, key: problem.key || "—" };
  if (problem.column === null) {
    return t("csv.problem_row", { ...where, message: codeMessage(t, problem.code) });
  }
  const reason =
    problem.allowed.length > 0
      ? t("csv.allowed", { values: problem.allowed.join(", ") })
      : codeMessage(t, problem.code);
  const message = problem.value ? t("csv.problem_value", { value: problem.value, reason }) : reason;
  return t("csv.problem_cell", { ...where, column: problem.column, message });
}

/** Export a list as CSV, and import one after showing what it would do. */
export default function CsvTools({
  exportPath,
  importPath,
  filename,
  personalData = false,
  onImported,
}: {
  exportPath: string;
  importPath: string;
  filename: string;
  personalData?: boolean;
  onImported: () => void;
}) {
  const { t } = useTranslation();
  const input = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState<{ csv: string; report: ImportReport } | null>(null);
  const [done, setDone] = useState<ImportReport | null>(null);
  const [error, setError] = useState<unknown>(null);

  async function onFile(event: ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError(null);
    setDone(null);
    try {
      const csv = decodeCsv(await file.arrayBuffer());
      const report = await http.post<ImportReport>(importPath, { csv, dry_run: true });
      setPending({ csv, report });
    } catch (failure) {
      setError(failure);
    }
  }

  async function apply(): Promise<void> {
    if (!pending) return;
    try {
      const report = await http.post<ImportReport>(importPath, {
        csv: pending.csv,
        dry_run: false,
      });
      setPending(null);
      setDone(report);
      onImported();
    } catch (failure) {
      setError(failure);
    }
  }

  const report = pending?.report ?? done;

  return (
    <div className="mb-3xs">
      <div className="flex flex-wrap items-center gap-4xs">
        <button
          type="button"
          className="btn-small"
          onClick={() =>
            void http.download(exportPath, filename).catch((failure: unknown) => setError(failure))
          }
        >
          {t("common.export_csv")}
        </button>
        <button type="button" className="btn-small" onClick={() => input.current?.click()}>
          {t("common.import_csv")}
        </button>
        <input
          ref={input}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          aria-label={t("common.import_csv")}
          onChange={(event) => void onFile(event)}
        />
        {personalData && (
          <span className="text-sm text-content-secondary">{t("common.personal_data")}</span>
        )}
      </div>
      {error !== null && (
        <p role="alert" className="field-error">
          {errorMessage(t, error)}
        </p>
      )}
      {report && (
        <div role="status" className="notice-info mt-4xs">
          <p>
            {t(pending ? "csv.would" : "csv.did", {
              created: report.created,
              updated: report.updated,
              unchanged: report.unchanged,
            })}
          </p>
          {report.errors.length > 0 && (
            <>
              <p className="mt-5xs">{t(pending ? "csv.skipped_would" : "csv.skipped_did")}</p>
              <ul className="mt-5xs list-disc pl-2xs">
                {report.errors.map((problem) => (
                  <li key={`${problem.row}-${problem.column ?? ""}`}>
                    {problemMessage(t, problem)}
                  </li>
                ))}
              </ul>
            </>
          )}
          {pending && (
            <div className="mt-4xs flex gap-4xs">
              <button type="button" className="btn-small" onClick={() => void apply()}>
                {t("common.apply")}
              </button>
              <button type="button" className="btn-small" onClick={() => setPending(null)}>
                {t("common.cancel")}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

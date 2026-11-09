import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, http } from "../../api/client";
import { errorMessage } from "../../api/errors";
import type { WorkbookImportResult } from "../../api/types";
import { encode, FilePicker, ImportHistory, ImportResultView } from "./WorkbookImport";

/**
 * Import of researcher feedback from a Microsoft Forms export (R8.1.2), beside the workbook
 * import and like it: check first, read the report, then import what was checked. Importing a
 * newer export later adds only the responses that are new.
 */
export default function FeedbackImport() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<WorkbookImportResult | null>(null);
  const [checked, setChecked] = useState<string | null>(null);
  const [busy, setBusy] = useState<"check" | "import" | null>(null);
  const [error, setError] = useState<unknown>(null);
  const choice = JSON.stringify([file?.name, file?.size, file?.lastModified]);

  async function run(commit: boolean): Promise<void> {
    if (!file) return;
    setBusy(commit ? "import" : "check");
    setError(null);
    try {
      const answer = await http.post<WorkbookImportResult>("/imports/feedback", {
        file: await encode(file),
        commit,
        language: i18n.language === "ja" ? "ja" : "en",
      });
      setResult(answer);
      setChecked(commit ? null : choice);
      if (commit) void queryClient.invalidateQueries();
      else void queryClient.invalidateQueries({ queryKey: ["imports"] });
    } catch (failure) {
      setError(failure);
      setResult(null);
    } finally {
      setBusy(null);
    }
  }

  const missing =
    error instanceof ApiError && typeof error.body.column === "string"
      ? t("settings.import.missing_column", { column: error.body.column })
      : null;
  const canImport = result !== null && !result.committed && checked === choice;

  return (
    <div className="max-w-3xl">
      <p className="mb-3xs text-content-secondary">{t("settings.feedback.help")}</p>
      <FilePicker
        id="import-feedback"
        label={t("settings.feedback.file")}
        file={file}
        onPick={setFile}
      />
      <button
        type="button"
        className="btn-quiet"
        disabled={!file || busy !== null}
        onClick={() => void run(false)}
      >
        {busy === "check" ? t("settings.import.checking") : t("settings.import.check")}
      </button>
      {error !== null && (
        <p role="alert" className="notice-error mt-3xs">
          {errorMessage(t, error)} {missing}
        </p>
      )}
      {result && (
        <ImportResultView
          result={result}
          levels={t("settings.feedback.levels", {
            check: result.levels.check ?? 0,
            info: result.levels.info ?? 0,
          })}
          canImport={canImport}
          busy={busy}
          onImport={() => void run(true)}
          checkAgain={t("settings.feedback.check_again")}
        />
      )}
      <ImportHistory kind="feedback" />
    </div>
  );
}

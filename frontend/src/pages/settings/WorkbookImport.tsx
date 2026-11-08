import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, http } from "../../api/client";
import { errorMessage } from "../../api/errors";
import type {
  PersonalFieldOwners,
  UploadedFile,
  User,
  WorkbookImportResult,
} from "../../api/types";

// The personal fields seeded from the workbook (BRIEF §6.6), by the key the server uses.
const PERSONAL_FIELDS = [
  ["bitly", "Bitly clicks, 28 days"],
  ["pitches", "Pitches"],
  ["request_received", "Request received"],
] as const;
type OwnerKey = (typeof PERSONAL_FIELDS)[number][0];

async function encode(file: File): Promise<UploadedFile> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  // In pieces, as one call with every byte as an argument overflows the stack.
  for (let start = 0; start < bytes.length; start += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(start, start + 0x8000));
  }
  return { name: file.name, content: btoa(binary) };
}

function save(text: string, name: string, type: string): void {
  // A byte-order mark, so Excel reads the Japanese in a CSV right.
  const body = type.startsWith("text/csv") ? `\uFEFF${text}` : text;
  const url = URL.createObjectURL(new Blob([body], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function FilePicker({
  id,
  label,
  file,
  onPick,
}: {
  id: string;
  label: string;
  file: File | null;
  onPick: (file: File | null) => void;
}) {
  return (
    <div className="mb-4xs">
      <label htmlFor={id} className="field-label">
        {label}
      </label>
      <input
        id={id}
        type="file"
        accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        onChange={(event) => onPick(event.target.files?.[0] ?? null)}
      />
      {file && <span className="sr-only">{file.name}</span>}
    </div>
  );
}

/**
 * Import of the old workbook (BRIEF step 1.8). Check first: the dry run changes nothing and
 * reports everything to look at. Import then does exactly what was checked.
 */
export default function WorkbookImport() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const [releaseList, setReleaseList] = useState<File | null>(null);
  const [intake, setIntake] = useState<File | null>(null);
  const [owners, setOwners] = useState<Record<OwnerKey, string>>({
    bitly: "",
    pitches: "",
    request_received: "",
  });
  const [result, setResult] = useState<WorkbookImportResult | null>(null);
  // The choices the shown dry run was made with: Import is offered only for those.
  const [checked, setChecked] = useState<string | null>(null);
  const [busy, setBusy] = useState<"check" | "import" | null>(null);
  const [error, setError] = useState<unknown>(null);
  const { data: users = [] } = useQuery({
    queryKey: ["users"],
    queryFn: () => http.get<User[]>("/users"),
  });
  const possibleOwners = users.filter((user) => user.is_active && user.role !== "viewer");

  const choices = JSON.stringify([
    releaseList?.name,
    releaseList?.size,
    releaseList?.lastModified,
    intake?.name,
    intake?.size,
    intake?.lastModified,
    owners,
  ]);

  async function run(commit: boolean): Promise<void> {
    if (!releaseList || !intake) return;
    setBusy(commit ? "import" : "check");
    setError(null);
    try {
      const chosen: PersonalFieldOwners = {
        bitly: owners.bitly || null,
        pitches: owners.pitches || null,
        request_received: owners.request_received || null,
      };
      const answer = await http.post<WorkbookImportResult>("/imports/workbook", {
        release_list: await encode(releaseList),
        intake: await encode(intake),
        owners: chosen,
        commit,
        language: i18n.language === "ja" ? "ja" : "en",
      });
      setResult(answer);
      setChecked(commit ? null : choices);
      if (commit) void queryClient.invalidateQueries();
    } catch (failure) {
      setError(failure);
      setResult(null);
    } finally {
      setBusy(null);
    }
  }

  const problemDetail =
    error instanceof ApiError && typeof error.body.column === "string"
      ? t("settings.import.missing_column", { column: error.body.column })
      : error instanceof ApiError && typeof error.body.sheet === "string"
        ? t("settings.import.missing_sheet", { sheet: error.body.sheet })
        : null;
  const canImport = result !== null && !result.committed && checked === choices;

  return (
    <div className="max-w-3xl">
      <p className="mb-3xs text-content-secondary">{t("settings.import.help")}</p>
      <FilePicker
        id="import-release-list"
        label={t("settings.import.release_list")}
        file={releaseList}
        onPick={setReleaseList}
      />
      <FilePicker
        id="import-intake"
        label={t("settings.import.intake")}
        file={intake}
        onPick={setIntake}
      />
      <fieldset className="mb-3xs">
        <legend className="field-label">{t("settings.import.owners")}</legend>
        <p className="mb-4xs text-sm text-content-secondary">{t("settings.import.owners_help")}</p>
        {PERSONAL_FIELDS.map(([key, label]) => (
          <label key={key} className="mb-5xs flex flex-wrap items-center gap-4xs">
            <span className="w-48">{label}</span>
            <select
              className="input max-w-xs"
              value={owners[key]}
              onChange={(event) => setOwners({ ...owners, [key]: event.target.value })}
            >
              <option value="">{t("settings.import.not_imported")}</option>
              {possibleOwners.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.full_name ?? user.email}
                </option>
              ))}
            </select>
          </label>
        ))}
      </fieldset>
      <div className="flex flex-wrap items-center gap-4xs">
        <button
          type="button"
          className="btn-quiet"
          disabled={!releaseList || !intake || busy !== null}
          onClick={() => void run(false)}
        >
          {busy === "check" ? t("settings.import.checking") : t("settings.import.check")}
        </button>
        <span className="text-sm text-content-secondary">{t("settings.import.takes_time")}</span>
      </div>
      {error !== null && (
        <p role="alert" className="notice-error mt-3xs">
          {errorMessage(t, error)} {problemDetail}
        </p>
      )}

      {result && (
        <section className="mt-2xs" aria-live="polite">
          <h4 className="mb-4xs font-semibold">
            {result.committed ? t("settings.import.done") : t("settings.import.dry_run")}
          </h4>
          <dl className="grid gap-x-2xs gap-y-5xs sm:grid-cols-[18rem_auto]">
            {result.summary.map((line) => (
              <div key={line.label} className="contents">
                <dt>{line.label}</dt>
                <dd className="tabular-nums">{line.count}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-4xs">
            {t("settings.import.levels", {
              check: result.levels.check ?? 0,
              dash: result.levels.dash ?? 0,
              info: result.levels.info ?? 0,
            })}
          </p>
          <div className="mt-4xs flex flex-wrap items-center gap-4xs">
            <button
              type="button"
              className="btn-small"
              onClick={() => save(result.markdown, `${result.filename}.md`, "text/markdown")}
            >
              {t("settings.import.report_md")}
            </button>
            <button
              type="button"
              className="btn-small"
              onClick={() =>
                save(result.csv, `${result.filename}.csv`, "text/csv;charset=utf-8")
              }
            >
              {t("settings.import.report_csv")}
            </button>
            <span className="text-sm text-content-secondary">{t("common.personal_data")}</span>
          </div>
          {!result.committed && (
            <div className="mt-3xs">
              <p className="notice-info mb-4xs">{t("settings.import.before_import")}</p>
              <button
                type="button"
                className="btn-primary"
                disabled={!canImport || busy !== null}
                onClick={() => void run(true)}
              >
                {busy === "import" ? t("settings.import.importing") : t("settings.import.import")}
              </button>
              {!canImport && busy === null && (
                <p className="mt-5xs text-sm text-content-secondary">
                  {t("settings.import.check_again")}
                </p>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

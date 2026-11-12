import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, http } from "../../api/client";
import { errorMessage } from "../../api/errors";
import type {
  ColumnAction,
  ColumnChoice,
  ColumnFieldType,
  ImportColumn,
  ImportKind,
  ImportRun,
  UploadedFile,
  User,
  WorkbookImportResult,
} from "../../api/types";
import { useBrand } from "../../brand";
import { formatDateTime } from "../../dates";

const FIELD_TYPES: ColumnFieldType[] = ["integer", "number", "date", "text"];

export async function encode(file: File): Promise<UploadedFile> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  // In pieces, as one call with every byte as an argument overflows the stack.
  for (let start = 0; start < bytes.length; start += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(start, start + 0x8000));
  }
  return { name: file.name, content: btoa(binary) };
}

export function save(text: string, name: string, type: string): void {
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

/** Every check and import so far, newest first, each with its report to download again. */
export function ImportHistory({ kind }: { kind: ImportKind }) {
  const { t, i18n } = useTranslation();
  const { timezone } = useBrand();
  const [error, setError] = useState<unknown>(null);
  const { data: runs = [] } = useQuery({
    queryKey: ["imports", kind],
    queryFn: () => http.get<ImportRun[]>(`/imports?kind=${kind}`),
  });
  if (runs.length === 0) return null;
  const language = i18n.language === "ja" ? "ja" : "en";

  function download(run: ImportRun, format: "md" | "csv"): void {
    setError(null);
    void http
      .download(
        `/imports/${run.id}/report?format=${format}&language=${language}`,
        `release_radar_import_report.${format}`,
      )
      .catch((failure: unknown) => setError(failure));
  }

  return (
    <div className="mt-2xs">
      <h4 className="mb-4xs font-semibold">{t("settings.import.history")}</h4>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("settings.import.history_when")}</th>
              <th>{t("settings.import.history_what")}</th>
              <th>{t("settings.import.history_who")}</th>
              <th>{t("settings.import.history_result")}</th>
              <th>{t("settings.import.history_report")}</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td className="whitespace-nowrap">
                  {formatDateTime(run.created_at, timezone)}
                </td>
                <td title={run.file_names.join(", ")}>
                  {run.committed
                    ? t("settings.import.kind_import")
                    : t("settings.import.kind_check")}
                </td>
                <td>{run.user_name ?? "—"}</td>
                <td>
                  {kind === "feedback"
                    ? t("settings.feedback.history_counts", {
                        new: run.counts.feedback_new ?? 0,
                        already: run.counts.feedback_already ?? 0,
                        check: run.levels.check ?? 0,
                      })
                    : t("settings.import.history_counts", {
                        new: run.counts.releases_new ?? 0,
                        updated: run.counts.releases_updated ?? 0,
                        check: run.levels.check ?? 0,
                      })}
                </td>
                <td className="whitespace-nowrap">
                  <button
                    type="button"
                    className="btn-small"
                    onClick={() => download(run, "md")}
                  >
                    Markdown
                  </button>{" "}
                  <button
                    type="button"
                    className="btn-small"
                    onClick={() => download(run, "csv")}
                  >
                    CSV
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {error !== null && (
        <p role="alert" className="field-error">
          {errorMessage(t, error)}
        </p>
      )}
    </div>
  );
}

export function FilePicker({
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
 * Check and Import side by side, from the start (Daniel looked for Import, 2026-11-12). Import
 * is ready once a check has been made with exactly what is chosen now, and does just that.
 */
export function CheckAndImport({
  ready,
  busy,
  checked,
  canImport,
  onCheck,
  onImport,
  changed,
}: {
  /** The files are chosen. */
  ready: boolean;
  busy: "check" | "import" | null;
  /** A check has been made this visit (and not imported since). */
  checked: boolean;
  canImport: boolean;
  onCheck: () => void;
  onImport: () => void;
  /** Says why Import waits when the choices changed since the check. */
  changed: string;
}) {
  const { t } = useTranslation();
  const hint = canImport
    ? t("settings.import.before_import")
    : checked
      ? changed
      : t("settings.import.check_first");
  return (
    <div className="mt-3xs">
      <div className="flex flex-wrap items-center gap-4xs">
        <button
          type="button"
          className={canImport ? "btn-quiet" : "btn-primary"}
          disabled={!ready || busy !== null}
          onClick={onCheck}
        >
          {busy === "check"
            ? t("settings.import.checking")
            : checked
              ? t("settings.import.check_again_button")
              : t("settings.import.check")}
        </button>
        <button
          type="button"
          className={canImport ? "btn-primary" : "btn-quiet"}
          disabled={!canImport || busy !== null}
          onClick={onImport}
        >
          {busy === "import"
            ? t("settings.import.importing")
            : t("settings.import.import")}
        </button>
        <span className="text-sm text-content-secondary">
          {t("settings.import.takes_time")}
        </span>
      </div>
      <p
        className={
          canImport
            ? "notice-info mt-4xs"
            : "mt-4xs text-sm text-content-secondary"
        }
      >
        {hint}
      </p>
    </div>
  );
}

/** What a check or an import did: the counts and the report to download. */
export function ImportResultView({
  result,
  levels,
}: {
  result: WorkbookImportResult;
  levels: string;
}) {
  const { t } = useTranslation();
  return (
    <section className="mt-2xs" aria-live="polite">
      <h4 className="mb-4xs font-semibold">
        {result.committed
          ? t("settings.import.done")
          : t("settings.import.dry_run")}
      </h4>
      <dl className="grid gap-x-2xs gap-y-5xs sm:grid-cols-[18rem_auto]">
        {result.summary.map((line) => (
          <div key={line.label} className="contents">
            <dt>{line.label}</dt>
            <dd className="tabular-nums">{line.count}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-4xs">{levels}</p>
      <div className="mt-4xs flex flex-wrap items-center gap-4xs">
        <button
          type="button"
          className="btn-small"
          onClick={() =>
            save(result.markdown, `${result.filename}.md`, "text/markdown")
          }
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
        <span className="text-sm text-content-secondary">
          {t("common.personal_data")}
        </span>
      </div>
    </section>
  );
}

function columnName(column: ImportColumn): string {
  return column.group ? `${column.heading} (${column.group})` : column.heading;
}

/**
 * The workbook's columns that have no place of their own (Daniel, 2026-11-12). One a field
 * remembers fills that field again. For a new one the admin chooses: leave it out, a shared
 * field for everyone, or a private field for each chosen person (a copy each).
 */
function OtherColumns({
  columns,
  choices,
  people,
  onChoose,
}: {
  columns: ImportColumn[];
  choices: Record<string, ColumnChoice>;
  people: User[];
  onChoose: (choice: ColumnChoice) => void;
}) {
  const { t } = useTranslation();
  const known = columns.filter((column) => column.known);
  const fresh = columns.filter((column) => !column.known);
  if (columns.length === 0) return null;
  return (
    <section className="mb-3xs" aria-labelledby="import-columns">
      <h4 id="import-columns" className="mb-5xs font-semibold">
        {t("settings.import.columns_title")}
      </h4>
      {fresh.length > 0 && (
        <>
          <p className="mb-4xs text-sm text-content-secondary">
            {t("settings.import.columns_help")}
          </p>
          <ul className="flex flex-col gap-3xs">
            {fresh.map((column) => {
              const choice = choices[column.key] ?? {
                key: column.key,
                action: "skip" as ColumnAction,
                field_type: column.suggested_type,
                owners: [],
              };
              const name = columnName(column);
              const id = `column-${column.key.replace(/[^A-Za-z0-9]+/g, "-")}`;
              return (
                <li
                  key={column.key}
                  className="rounded border border-line-disabled p-4xs"
                >
                  <p className="font-semibold">{name}</p>
                  <p className="mb-4xs text-sm text-content-secondary">
                    {column.examples.length > 0
                      ? t("settings.import.column_examples", {
                          examples: column.examples.join(" · "),
                        })
                      : t("settings.import.column_empty")}
                  </p>
                  <div className="flex flex-wrap items-center gap-4xs">
                    <label className="flex items-center gap-5xs text-sm">
                      <span className="sr-only">
                        {t("settings.import.column_action", { name })}
                      </span>
                      <select
                        id={`${id}-action`}
                        className="input w-auto"
                        aria-label={t("settings.import.column_action", {
                          name,
                        })}
                        value={choice.action}
                        onChange={(event) =>
                          onChoose({
                            ...choice,
                            action: event.target.value as ColumnAction,
                          })
                        }
                      >
                        <option value="skip">
                          {t("settings.import.column_skip")}
                        </option>
                        <option value="shared">
                          {t("settings.import.column_shared")}
                        </option>
                        <option value="personal">
                          {t("settings.import.column_personal")}
                        </option>
                      </select>
                    </label>
                    {choice.action !== "skip" && (
                      <select
                        className="input w-auto"
                        aria-label={t("settings.import.column_type", { name })}
                        value={choice.field_type}
                        onChange={(event) =>
                          onChoose({
                            ...choice,
                            field_type: event.target.value as ColumnFieldType,
                          })
                        }
                      >
                        {FIELD_TYPES.map((type) => (
                          <option key={type} value={type}>
                            {t(`settings.import.column_types.${type}`)}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
                  {choice.action === "personal" && (
                    <fieldset className="mt-4xs">
                      <legend className="text-sm">
                        {t("settings.import.column_owners", { name })}
                      </legend>
                      <div className="mt-5xs flex flex-wrap gap-x-xs gap-y-5xs">
                        {people.map((person) => (
                          <label
                            key={person.id}
                            className="flex items-center gap-5xs text-sm"
                          >
                            <input
                              type="checkbox"
                              checked={choice.owners.includes(person.id)}
                              onChange={(event) =>
                                onChoose({
                                  ...choice,
                                  owners: event.target.checked
                                    ? [...choice.owners, person.id]
                                    : choice.owners.filter(
                                        (owner) => owner !== person.id,
                                      ),
                                })
                              }
                            />
                            {person.full_name ?? person.email}
                          </label>
                        ))}
                      </div>
                    </fieldset>
                  )}
                  {column.fills.length > 0 && (
                    <p className="mt-4xs text-sm">
                      {t("settings.import.column_fills", {
                        fields: column.fills
                          .map((fill) =>
                            fill.owner
                              ? `${fill.label} (${fill.owner})`
                              : fill.label,
                          )
                          .join(", "),
                      })}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </>
      )}
      {known.length > 0 && (
        <>
          <p className="mb-5xs mt-3xs text-sm text-content-secondary">
            {t("settings.import.columns_known")}
          </p>
          <ul className="list-disc pl-xs text-sm">
            {known.map((column) => (
              <li key={column.key}>
                {columnName(column)} →{" "}
                {column.fills
                  .map((fill) =>
                    fill.owner ? `${fill.label} (${fill.owner})` : fill.label,
                  )
                  .join(", ")}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
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
  const [columnChoices, setColumnChoices] = useState<
    Record<string, ColumnChoice>
  >({});
  const [columns, setColumns] = useState<ImportColumn[]>([]);
  const [fillEmptyOnly, setFillEmptyOnly] = useState(false);
  const [result, setResult] = useState<WorkbookImportResult | null>(null);
  // The choices the shown check was made with: Import is offered only for those.
  const [checked, setChecked] = useState<string | null>(null);
  const [busy, setBusy] = useState<"check" | "import" | null>(null);
  const [error, setError] = useState<unknown>(null);
  const { data: users = [] } = useQuery({
    queryKey: ["users"],
    queryFn: () => http.get<User[]>("/users"),
  });
  const people = users.filter(
    (user) => user.is_active && user.role !== "viewer",
  );

  // Only what will do something; a column left out needs no mention.
  const sent = Object.values(columnChoices).filter(
    (choice) =>
      choice.action === "shared" ||
      (choice.action === "personal" && choice.owners.length > 0),
  );
  const choices = JSON.stringify([
    releaseList?.name,
    releaseList?.size,
    releaseList?.lastModified,
    intake?.name,
    intake?.size,
    intake?.lastModified,
    sent,
    fillEmptyOnly,
  ]);

  async function run(commit: boolean): Promise<void> {
    if (!releaseList) return;
    setBusy(commit ? "import" : "check");
    setError(null);
    try {
      const answer = await http.post<WorkbookImportResult>(
        "/imports/workbook",
        {
          release_list: await encode(releaseList),
          intake: intake ? await encode(intake) : null,
          columns: sent,
          fill_empty_only: fillEmptyOnly,
          commit,
          language: i18n.language === "ja" ? "ja" : "en",
        },
      );
      setResult(answer);
      setColumns(answer.columns ?? []);
      setChecked(commit ? null : choices);
      // After an import everything may have changed; after a check, only the history.
      if (commit) void queryClient.invalidateQueries();
      else void queryClient.invalidateQueries({ queryKey: ["imports"] });
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
      <p className="mb-3xs text-content-secondary">
        {t("settings.import.help")}
      </p>
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
      <p className="-mt-5xs mb-3xs text-sm text-content-secondary">
        {t("settings.import.intake_help")}
      </p>
      <label className="mb-3xs flex items-start gap-4xs">
        <input
          type="checkbox"
          className="mt-5xs"
          checked={fillEmptyOnly}
          onChange={(event) => setFillEmptyOnly(event.target.checked)}
        />
        <span>
          <span className="font-semibold">
            {t("settings.import.fill_empty_only")}
          </span>
          <span className="block text-sm text-content-secondary">
            {t("settings.import.fill_empty_only_help")}
          </span>
        </span>
      </label>
      <OtherColumns
        columns={columns}
        choices={columnChoices}
        people={people}
        onChoose={(choice) =>
          setColumnChoices((current) => ({ ...current, [choice.key]: choice }))
        }
      />
      <CheckAndImport
        ready={releaseList !== null}
        busy={busy}
        checked={checked !== null}
        canImport={canImport}
        onCheck={() => void run(false)}
        onImport={() => void run(true)}
        changed={t("settings.import.check_again")}
      />
      {error !== null && (
        <p role="alert" className="notice-error mt-3xs">
          {errorMessage(t, error)} {problemDetail}
        </p>
      )}

      {result && (
        <ImportResultView
          result={result}
          levels={t("settings.import.levels", {
            check: result.levels.check ?? 0,
            dash: result.levels.dash ?? 0,
            info: result.levels.info ?? 0,
          })}
        />
      )}
      <ImportHistory kind="workbook" />
    </div>
  );
}

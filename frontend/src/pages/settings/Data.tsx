import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { http } from "../../api/client";
import { errorMessage } from "../../api/errors";
import type { BackupStatus, JobRun } from "../../api/types";
import { useBrand } from "../../brand";
import { useToast } from "../../components/Toast";
import { formatDateTime } from "../../dates";
import { SectionHeader, SubHeading } from "./SettingsLayout";
import FeedbackImport from "./FeedbackImport";
import WorkbookImport from "./WorkbookImport";

function formatSize(bytes: number): string {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const KNOWN_JOBS = [
  "backup-nightly",
  "backup-manual",
  "housekeeping",
  "ga4-website-views",
  "ga4-website-views-manual",
  "scheduler-test",
] as const;

function isKnownJob(key: string): key is (typeof KNOWN_JOBS)[number] {
  return (KNOWN_JOBS as readonly string[]).includes(key);
}

export default function DataSettings() {
  const { t } = useTranslation();
  const { timezone } = useBrand();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [error, setError] = useState<unknown>(null);
  const { data: backup } = useQuery({
    queryKey: ["backups", "status"],
    queryFn: () => http.get<BackupStatus>("/backups/status"),
    refetchInterval: 15_000,
  });
  const { data: runs } = useQuery({
    queryKey: ["jobs", "runs"],
    queryFn: () => http.get<JobRun[]>("/jobs/runs?limit=10"),
    refetchInterval: 15_000,
  });
  const when = (value: string) => formatDateTime(value, timezone);
  const lastRun = backup?.last_run;

  async function backUpNow(): Promise<void> {
    setError(null);
    try {
      await http.post("/backups/run");
      toast({ text: t("settings.data.backup_started") });
      setTimeout(() => void queryClient.invalidateQueries({ queryKey: ["backups"] }), 2000);
      setTimeout(() => void queryClient.invalidateQueries({ queryKey: ["jobs"] }), 2000);
    } catch (failure) {
      setError(failure);
    }
  }

  function exportAll(format: "json" | "xlsx"): void {
    setError(null);
    void http
      .download(`/settings/export?format=${format}`, `release_radar.${format}`)
      .catch((failure: unknown) => setError(failure));
  }

  return (
    <div>
      <SectionHeader title={t("settings.sections.data")} help={t("settings.help.data")} />
      {error !== null && (
        <p role="alert" className="notice-error mb-2xs max-w-3xl">
          {errorMessage(t, error)}
        </p>
      )}

      <SubHeading>{t("settings.data.backup_title")}</SubHeading>
      {backup && (
        <dl className="grid max-w-3xl gap-x-2xs gap-y-5xs sm:grid-cols-[12rem_1fr]">
          <dt className="font-semibold">{t("settings.data.backup_latest")}</dt>
          <dd>
            {backup.latest
              ? `${when(backup.latest.created_at)} · ${formatSize(backup.latest.size_bytes)}`
              : t("settings.data.backup_none")}
          </dd>
          <dt className="font-semibold">{t("settings.data.backup_keeps")}</dt>
          <dd>{t("settings.data.backup_retention", { days: backup.retention_days })}</dd>
          {lastRun && (
            <>
              <dt className="font-semibold">{t("settings.data.backup_last_run")}</dt>
              <dd>
                {when(lastRun.started_at)} · {t(`settings.data.status.${lastRun.status}`)}
                {lastRun.status !== "succeeded" && lastRun.detail && (
                  <p className="text-content-secondary">{lastRun.detail}</p>
                )}
              </dd>
            </>
          )}
        </dl>
      )}
      {backup && !backup.configured && (
        <p role="status" className="notice-info mt-4xs max-w-3xl">
          {t("settings.data.backup_not_configured")}
        </p>
      )}
      <button
        type="button"
        className="btn-quiet mt-3xs"
        disabled={!backup?.configured}
        onClick={() => void backUpNow()}
      >
        {t("settings.data.backup_now")}
      </button>

      <SubHeading>{t("settings.data.export_title")}</SubHeading>
      <p className="mb-4xs max-w-3xl text-content-secondary">{t("settings.data.export_help")}</p>
      <div className="flex flex-wrap items-center gap-4xs">
        <button type="button" className="btn-quiet" onClick={() => exportAll("json")}>
          {t("settings.data.export_json")}
        </button>
        <button type="button" className="btn-quiet" onClick={() => exportAll("xlsx")}>
          {t("settings.data.export_xlsx")}
        </button>
        <span className="text-sm text-content-secondary">{t("common.personal_data")}</span>
      </div>

      <SubHeading>{t("settings.data.import_title")}</SubHeading>
      <WorkbookImport />

      <SubHeading>{t("settings.data.feedback_title")}</SubHeading>
      <FeedbackImport />

      <SubHeading>{t("settings.data.jobs_title")}</SubHeading>
      {runs && runs.length > 0 ? (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t("settings.data.job")}</th>
                <th>{t("settings.data.job_when")}</th>
                <th>{t("settings.data.job_result")}</th>
                <th>{t("settings.data.job_detail")}</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={`${run.job_key}-${run.slot}`}>
                  <td className="whitespace-nowrap">
                    {isKnownJob(run.job_key) ? t(`settings.data.jobs.${run.job_key}`) : run.job_key}
                  </td>
                  <td className="whitespace-nowrap">{when(run.started_at)}</td>
                  <td>{t(`settings.data.status.${run.status}`)}</td>
                  <td className="text-content-secondary">{run.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-content-secondary">{t("settings.data.jobs_none")}</p>
      )}
    </div>
  );
}

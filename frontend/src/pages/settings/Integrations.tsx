import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ApiError, http } from "../../api/client";
import { errorMessage } from "../../api/errors";
import type { Ga4Status, Ga4TestResult } from "../../api/types";
import { useBrand } from "../../brand";
import ConfirmButton from "../../components/ConfirmButton";
import { TextField } from "../../components/fields/Autosave";
import { useFieldSaver } from "../../components/fields/useFieldSaver";
import { useToast } from "../../components/Toast";
import { formatDate, formatDateTime } from "../../dates";
import { headingId } from "../Manual";
import { SectionHeader, SubHeading } from "./SettingsLayout";

const PATH = "/integrations/ga4";
export const GA4_QUERY = ["integrations", "ga4"];
// After Fetch now, how long the page keeps looking for the run to start and finish.
const WATCH_MS = 10 * 60 * 1000;

const TEST_CODES = [
  "connected",
  "connected_no_views",
  "key_rejected",
  "api_disabled",
  "no_access",
  "wrong_property",
  "quota",
  "unreachable",
  "google_error",
] as const;

function isTestCode(code: string): code is (typeof TEST_CODES)[number] {
  return (TEST_CODES as readonly string[]).includes(code);
}

/** What a test found, in plain words (phase-2 brief §3.1). */
export function TestOutcome({ result }: { result: Ga4TestResult }) {
  const { t } = useTranslation();
  const { timezone } = useBrand();
  const values = {
    views: (result.views ?? 0).toLocaleString(),
    host: result.host ?? "",
    date: formatDate(result.date, timezone),
  };
  const code = isTestCode(result.code) ? result.code : "google_error";
  const text =
    code === "connected" && !result.host
      ? t("settings.integrations.ga4.test.connected_any_host", values)
      : t(`settings.integrations.ga4.test.${code}`, values);
  return (
    <p role="status" className={`${result.ok ? "notice-info" : "notice-error"} mt-4xs max-w-3xl`}>
      {text}
      {!result.ok && result.detail && (
        <span className="block text-sm text-content-secondary">
          {t("settings.integrations.ga4.google_said", {
            detail: result.detail,
          })}
        </span>
      )}
    </p>
  );
}

function KeyPicker({ configured, onSaved }: { configured: boolean; onSaved: () => void }) {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const id = useId();
  const [error, setError] = useState<unknown>(null);

  async function pick(input: HTMLInputElement): Promise<void> {
    const file = input.files?.[0];
    if (!file) return;
    setError(null);
    try {
      // Read here and sent once, to this install only. Never kept in the page.
      const status = await http.put<Ga4Status>(`${PATH}/key`, {
        key: await file.text(),
      });
      queryClient.setQueryData(GA4_QUERY, status);
      toast({ text: t("settings.integrations.ga4.key_saved") });
      onSaved();
    } catch (failure) {
      setError(failure);
    } finally {
      input.value = "";
    }
  }

  return (
    <div>
      <label className="field-label" htmlFor={id}>
        {configured
          ? t("settings.integrations.ga4.key_replace")
          : t("settings.integrations.ga4.key_choose")}
      </label>
      <input
        id={id}
        type="file"
        accept=".json,application/json"
        onChange={(event) => void pick(event.target)}
      />
      <p className="field-hint">{t("settings.integrations.ga4.key_hint")}</p>
      {error !== null && (
        <p role="alert" className="notice-error mt-5xs">
          {errorMessage(t, error)}
        </p>
      )}
    </div>
  );
}

/** Settings → Integrations: Google Analytics for website views (R8.1.1). */
export default function IntegrationsSettings() {
  const { t } = useTranslation();
  const { timezone } = useBrand();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [watchUntil, setWatchUntil] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const [testing, setTesting] = useState(false);
  const [test, setTest] = useState<Ga4TestResult | null>(null);
  const { data } = useQuery({
    queryKey: GA4_QUERY,
    queryFn: () => http.get<Ga4Status>(PATH),
    refetchInterval: (query) =>
      query.state.data?.running || Date.now() < watchUntil ? 3000 : false,
  });
  const saver = useFieldSaver(PATH, GA4_QUERY);
  if (!data) return null;

  const ready = data.configured && data.readable && Boolean(data.property_id);
  const shownTest = test ?? data.last_test;
  const when = (value: string) => formatDateTime(value, timezone);
  const refresh = () => void queryClient.invalidateQueries({ queryKey: GA4_QUERY });

  async function runTest(): Promise<void> {
    setError(null);
    setTesting(true);
    try {
      setTest(await http.post<Ga4TestResult>(`${PATH}/test`));
      refresh();
    } catch (failure) {
      setError(failure);
    } finally {
      setTesting(false);
    }
  }

  async function fetchNow(): Promise<void> {
    setError(null);
    try {
      await http.post(`${PATH}/fetch`);
      toast({ text: t("settings.integrations.ga4.fetch_started") });
      setWatchUntil(Date.now() + WATCH_MS);
      refresh();
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    } catch (failure) {
      setError(failure);
    }
  }

  async function removeKey(): Promise<void> {
    setError(null);
    try {
      await http.delete(`${PATH}/key`);
      toast({ text: t("settings.integrations.ga4.key_removed") });
    } catch (failure) {
      setError(failure);
    }
    setTest(null);
    refresh();
  }

  let connection: string;
  if (!data.configured) connection = t("settings.integrations.ga4.not_connected");
  else if (!data.readable) connection = t("settings.integrations.ga4.key_unreadable");
  else
    connection = data.project_id
      ? t("settings.integrations.ga4.connected_as_project", {
          email: data.client_email,
          project: data.project_id,
        })
      : t("settings.integrations.ga4.connected_as", {
          email: data.client_email,
        });
  const notReady = error instanceof ApiError && error.code.startsWith("ga4_") ? null : error;

  return (
    <div>
      <SectionHeader
        title={t("settings.sections.integrations")}
        help={t("settings.help.integrations")}
      />
      {notReady !== null && (
        <p role="alert" className="notice-error mb-2xs max-w-3xl">
          {errorMessage(t, notReady)}
        </p>
      )}

      <SubHeading>{t("settings.integrations.ga4.title")}</SubHeading>
      <p className="mb-3xs max-w-3xl text-content-secondary">
        {data.domain
          ? t("settings.integrations.ga4.help", { domain: data.domain })
          : t("settings.integrations.ga4.help_no_domain")}{" "}
        <Link to={`/manual#${headingId(t("settings.integrations.ga4.manual_heading"))}`}>
          {t("settings.integrations.ga4.manual")}
        </Link>
      </p>
      <p
        role="status"
        className={`${data.configured && !data.readable ? "notice-error" : "notice-info"} mb-3xs max-w-3xl`}
      >
        {connection}
      </p>

      <div className="grid max-w-3xl gap-2xs sm:grid-cols-2">
        <KeyPicker
          configured={data.configured}
          onSaved={() => {
            setTest(null);
          }}
        />
        <div>
          <label className="field-label" htmlFor="ga4-property">
            {t("settings.integrations.ga4.property")}
          </label>
          <TextField
            id="ga4-property"
            className="input"
            label={t("settings.integrations.ga4.property")}
            value={data.property_id}
            version={data.field_versions.property_id ?? 0}
            save={saver("property_id")}
            hint={t("settings.integrations.ga4.property_hint")}
          />
        </div>
      </div>

      <div className="mt-3xs flex flex-wrap items-center gap-4xs">
        <button
          type="button"
          className="btn-quiet"
          disabled={!ready || testing}
          onClick={() => void runTest()}
        >
          {testing
            ? t("settings.integrations.ga4.testing")
            : t("settings.integrations.ga4.test_button")}
        </button>
        <button
          type="button"
          className="btn-quiet"
          disabled={!ready || data.running}
          onClick={() => void fetchNow()}
        >
          {t("settings.integrations.ga4.fetch_now")}
        </button>
        {data.configured && (
          <ConfirmButton
            label={t("settings.integrations.ga4.remove_key")}
            question={t("settings.integrations.ga4.remove_question")}
            onConfirm={() => void removeKey()}
          />
        )}
      </div>
      {error instanceof ApiError && error.code.startsWith("ga4_") && (
        <p role="alert" className="notice-error mt-4xs max-w-3xl">
          {errorMessage(t, error)}
        </p>
      )}
      {shownTest && <TestOutcome result={shownTest} />}
      {!test && data.last_test_at && (
        <p className="mt-5xs text-sm text-content-secondary">
          {t("settings.integrations.ga4.last_tested", {
            when: when(data.last_test_at),
          })}
        </p>
      )}

      <SubHeading>{t("settings.integrations.ga4.views_title")}</SubHeading>
      <dl className="grid max-w-3xl gap-x-2xs gap-y-5xs sm:grid-cols-[12rem_1fr]">
        <dt className="font-semibold">{t("settings.integrations.ga4.schedule")}</dt>
        <dd>
          {data.first_fetch_at
            ? t("settings.integrations.ga4.schedule_daily", {
                when: when(data.first_fetch_at),
              })
            : t("settings.integrations.ga4.schedule_waiting")}
        </dd>
        <dt className="font-semibold">{t("settings.integrations.ga4.last_run")}</dt>
        <dd>
          {data.running ? (
            <span role="status">{t("settings.integrations.ga4.running")}</span>
          ) : data.last_run ? (
            <>
              {when(data.last_run.started_at)} · {t(`settings.data.status.${data.last_run.status}`)}
              {data.last_run.detail && (
                <p className="text-content-secondary">{data.last_run.detail}</p>
              )}
            </>
          ) : (
            t("settings.integrations.ga4.never_run")
          )}
        </dd>
        <dt className="font-semibold">{t("settings.integrations.ga4.counts")}</dt>
        <dd>
          {t("settings.integrations.ga4.counts_text", {
            fetched: data.fetched,
            waiting: data.waiting.length,
            open: data.not_yet_due,
          })}
        </dd>
      </dl>

      {data.waiting.length > 0 && (
        <>
          <h3 className="mb-5xs mt-xs text-xl">{t("settings.integrations.ga4.waiting_title")}</h3>
          <p className="mb-4xs max-w-3xl text-content-secondary">
            {data.first_fetch_at
              ? t("settings.integrations.ga4.waiting_help")
              : t("settings.integrations.ga4.waiting_help_before")}
          </p>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t("settings.integrations.ga4.code")}</th>
                  <th>{t("settings.integrations.ga4.release")}</th>
                  <th>{t("settings.integrations.ga4.release_date")}</th>
                  <th>{t("settings.integrations.ga4.page")}</th>
                </tr>
              </thead>
              <tbody>
                {data.waiting.map((item) => (
                  <tr key={item.release_id}>
                    <td className="whitespace-nowrap">{item.code ?? "—"}</td>
                    <td>
                      <Link to={`/data?view=all&release=${item.release_id}`}>
                        {item.title ?? t("data.no_title")}
                      </Link>
                    </td>
                    <td className="whitespace-nowrap">{formatDate(item.release_date, timezone)}</td>
                    <td className="break-all">
                      <a href={item.website_url} target="_blank" rel="noopener noreferrer">
                        {new URL(item.website_url, "https://x.invalid").pathname}
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

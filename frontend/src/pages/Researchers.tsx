import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { http } from "../api/client";
import { errorMessage } from "../api/errors";
import type { Researcher, ResearcherPage, Unit } from "../api/types";
import { useAuth } from "../auth";
import AddEntry from "../components/AddEntry";
import ConfirmButton from "../components/ConfirmButton";
import { SelectField, TextField } from "../components/fields/Autosave";
import { useFieldSaver } from "../components/fields/useFieldSaver";
import { useToast } from "../components/Toast";
import { SectionHeader } from "./settings/SettingsLayout";

const STATUSES = ["incomplete", "unverified", "verified"] as const;
const GENDERS = ["M", "F", "other", "not_recorded"] as const;
const PAGE_SIZE = 50;
const QUERY_KEY = ["researchers"];

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

function MergePanel({ researcher, onClose }: { researcher: Researcher; onClose: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [error, setError] = useState<unknown>(null);
  const term = useDebounced(search, 250);
  const { data } = useQuery({
    queryKey: ["researchers", "merge", term],
    queryFn: () =>
      http.get<ResearcherPage>(`/researchers?limit=8&search=${encodeURIComponent(term)}`),
    enabled: term.trim().length > 0,
  });
  const targets = (data?.items ?? []).filter((item) => item.id !== researcher.id);

  async function merge(target: Researcher): Promise<void> {
    setError(null);
    try {
      await http.post(`/researchers/${researcher.id}/merge`, { into_id: target.id });
      await queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast({ text: t("researchers.merged", { from: researcher.name, to: target.name }) });
      onClose();
    } catch (failure) {
      setError(failure);
    }
  }

  return (
    <tr>
      <td colSpan={11} className="bg-surface-secondary">
        <div className="max-w-3xl p-4xs">
          <label className="field-label" htmlFor={`merge-${researcher.id}`}>
            {t("researchers.merge_into", { name: researcher.name })}
          </label>
          <input
            id={`merge-${researcher.id}`}
            className="input"
            autoFocus
            placeholder={t("researchers.search")}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <p className="field-hint">{t("researchers.merge_hint")}</p>
          <ul className="mt-4xs space-y-5xs">
            {targets.map((target) => (
              <li key={target.id} className="flex flex-wrap items-center gap-4xs">
                <span>
                  {target.name}{" "}
                  <span className="text-sm text-content-secondary">
                    {t("researchers.release_total", { count: target.release_count })}
                  </span>
                </span>
                <ConfirmButton
                  label={t("researchers.merge_choose")}
                  question={t("researchers.merge_question", {
                    count: researcher.release_count,
                    name: target.name,
                  })}
                  onConfirm={() => void merge(target)}
                />
              </li>
            ))}
          </ul>
          {error !== null && (
            <p role="alert" className="field-error">
              {errorMessage(t, error)}
            </p>
          )}
          <button type="button" className="btn-small mt-4xs" onClick={onClose}>
            {t("common.cancel")}
          </button>
        </div>
      </td>
    </tr>
  );
}

function ResearcherRow({
  researcher,
  units,
  canEdit,
}: {
  researcher: Researcher;
  units: Unit[];
  canEdit: boolean;
}) {
  const { t, i18n } = useTranslation();
  const saver = useFieldSaver(`/researchers/${researcher.id}`, QUERY_KEY);
  const [merging, setMerging] = useState(false);
  const versions = researcher.field_versions;

  return (
    <>
      <tr>
        <td>
          <TextField
            label={t("researchers.name")}
            value={researcher.name}
            version={versions.name}
            save={saver("name")}
            disabled={!canEdit}
          />
        </td>
        <td>
          <TextField
            label={t("researchers.given_name")}
            value={researcher.given_name}
            version={versions.given_name}
            save={saver("given_name")}
            disabled={!canEdit}
          />
        </td>
        <td>
          <TextField
            label={t("researchers.family_name")}
            value={researcher.family_name}
            version={versions.family_name}
            save={saver("family_name")}
            disabled={!canEdit}
          />
        </td>
        <td>
          <TextField
            label={t("researchers.name_ja")}
            value={researcher.name_ja}
            version={versions.name_ja}
            save={saver("name_ja")}
            disabled={!canEdit}
          />
        </td>
        <td>
          <SelectField
            label={t("researchers.unit")}
            value={researcher.current_unit_id}
            version={versions.current_unit_id}
            save={saver("current_unit_id")}
            disabled={!canEdit}
            emptyLabel={t("common.none")}
            options={units.map((unit) => ({
              value: unit.id,
              label: (i18n.language === "ja" && unit.name_ja) || unit.name_en,
            }))}
          />
        </td>
        <td>
          <SelectField
            label={t("researchers.gender")}
            value={researcher.gender}
            version={versions.gender}
            save={saver("gender")}
            disabled={!canEdit}
            options={GENDERS.map((gender) => ({
              value: gender,
              label: t(`researchers.genders.${gender}`),
            }))}
          />
        </td>
        <td>
          <TextField
            label={t("researchers.researchmap")}
            value={researcher.researchmap_id}
            version={versions.researchmap_id}
            save={saver("researchmap_id")}
            disabled={!canEdit}
          />
        </td>
        <td>
          <TextField
            label={t("researchers.orcid")}
            value={researcher.orcid}
            version={versions.orcid}
            save={saver("orcid")}
            disabled={!canEdit}
          />
        </td>
        <td>
          <SelectField
            label={t("researchers.status")}
            value={researcher.status}
            version={versions.status}
            save={saver("status")}
            disabled={!canEdit}
            options={STATUSES.map((status) => ({
              value: status,
              label: t(`researchers.statuses.${status}`),
            }))}
          />
        </td>
        <td className="text-center">{researcher.release_count}</td>
        <td>
          {canEdit && (
            <button type="button" className="btn-small" onClick={() => setMerging((on) => !on)}>
              {t("researchers.merge")}
            </button>
          )}
        </td>
      </tr>
      {merging && <MergePanel researcher={researcher} onClose={() => setMerging(false)} />}
    </>
  );
}

/** The directory, for admins in Settings and for editors from the main navigation. */
export default function Researchers() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [limit, setLimit] = useState(PAGE_SIZE);
  const term = useDebounced(search, 250);
  const params = new URLSearchParams({ limit: String(limit) });
  if (term.trim()) params.set("search", term.trim());
  if (status) params.set("status", status);

  const { data } = useQuery({
    queryKey: [...QUERY_KEY, term, status, limit],
    queryFn: () => http.get<ResearcherPage>(`/researchers?${params.toString()}`),
    placeholderData: keepPreviousData,
    refetchInterval: 60_000,
  });
  const { data: units } = useQuery({
    queryKey: ["lists", "units"],
    queryFn: () => http.get<Unit[]>("/lists/units"),
  });
  const canEdit = user?.role === "admin" || user?.role === "editor";

  return (
    <div>
      <SectionHeader title={t("settings.sections.researchers")} help={t("settings.help.researchers")} />
      <div className="mb-2xs flex flex-wrap items-center gap-4xs">
        <input
          className="input max-w-md"
          type="search"
          aria-label={t("researchers.search")}
          placeholder={t("researchers.search")}
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setLimit(PAGE_SIZE);
          }}
        />
        <select
          className="input max-w-52"
          aria-label={t("researchers.status")}
          value={status}
          onChange={(event) => {
            setStatus(event.target.value);
            setLimit(PAGE_SIZE);
          }}
        >
          <option value="">{t("researchers.all_statuses")}</option>
          {STATUSES.map((item) => (
            <option key={item} value={item}>
              {t(`researchers.statuses.${item}`)}
            </option>
          ))}
        </select>
        {data && (
          <span className="text-sm text-content-secondary">
            {t("researchers.found", { count: data.total })}
          </span>
        )}
      </div>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("researchers.name")}</th>
              <th>{t("researchers.given_name")}</th>
              <th>{t("researchers.family_name")}</th>
              <th>{t("researchers.name_ja")}</th>
              <th>{t("researchers.unit")}</th>
              <th>{t("researchers.gender")}</th>
              <th>{t("researchers.researchmap")}</th>
              <th>{t("researchers.orcid")}</th>
              <th>{t("researchers.status")}</th>
              <th>{t("researchers.releases")}</th>
              <th>{t("common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {(data?.items ?? []).map((researcher) => (
              <ResearcherRow
                key={researcher.id}
                researcher={researcher}
                units={units ?? []}
                canEdit={canEdit}
              />
            ))}
          </tbody>
        </table>
      </div>
      {data && data.total > data.items.length && (
        <button
          type="button"
          className="btn-quiet mt-3xs"
          onClick={() => setLimit((current) => current + PAGE_SIZE)}
        >
          {t("common.show_more")}
        </button>
      )}
      {canEdit && (
        <AddEntry
          label={t("researchers.add")}
          onAdd={async (name) => {
            await http.post("/researchers", { name });
            await queryClient.invalidateQueries({ queryKey: QUERY_KEY });
          }}
        />
      )}
    </div>
  );
}

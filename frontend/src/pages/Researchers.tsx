import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import type { TFunction } from "i18next";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { http } from "../api/client";
import { errorMessage } from "../api/errors";
import type {
  Researcher,
  ResearcherDetail,
  ResearcherPage,
  ResearcherRelease,
  SplitResult,
  Unit,
} from "../api/types";
import { useAuth } from "../auth";
import { useBrand } from "../brand";
import AddEntry from "../components/AddEntry";
import { SelectField, TextField } from "../components/fields/Autosave";
import { useFieldSaver } from "../components/fields/useFieldSaver";
import { useToast } from "../components/Toast";
import { formatDate } from "../dates";
import { SectionHeader } from "./settings/SettingsLayout";

const STATUSES = ["incomplete", "unverified", "verified"] as const;
const GENDERS = ["M", "F", "other", "not_recorded"] as const;
const PAGE_SIZE = 50;
const QUERY_KEY = ["researchers"];
type PanelKind = "merge" | "split";

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

/**
 * Opens beside the table, not inside it: the table is wide and scrolls sideways, which would
 * carry a panel in one of its rows out of view.
 */
function SidePanel({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!panel.current?.contains(document.activeElement)) panel.current?.focus();
  }, []);
  return (
    <aside
      ref={panel}
      role="dialog"
      aria-label={title}
      tabIndex={-1}
      className="side-panel"
      onKeyDown={(event) => {
        if (event.key === "Escape") onClose();
      }}
    >
      <div className="mb-3xs flex items-start justify-between gap-4xs">
        <h2 className="font-semibold">{title}</h2>
        <button type="button" className="btn-small" onClick={onClose}>
          {t("common.cancel")}
        </button>
      </div>
      {children}
    </aside>
  );
}

/** Records to choose from, with what tells namesakes apart beside each name. */
function useRecordSearch(term: string, exclude: string) {
  const debounced = useDebounced(term, 250);
  const { data } = useQuery({
    queryKey: ["researchers", "search", debounced],
    queryFn: () =>
      http.get<ResearcherPage>(`/researchers?limit=8&search=${encodeURIComponent(debounced)}`),
    enabled: debounced.trim().length > 0,
  });
  return (data?.items ?? []).filter((item) => item.id !== exclude);
}

function RecordSummary({ record, units }: { record: Researcher; units: Unit[] }) {
  const { t, i18n } = useTranslation();
  const unit = units.find((item) => item.id === record.current_unit_id);
  const unitName = unit ? (i18n.language === "ja" && unit.name_ja) || unit.name_en : null;
  const details = [
    unitName,
    record.orcid,
    record.notes,
    t("researchers.release_total", { count: record.release_count }),
  ].filter(Boolean);
  return (
    <span>
      {record.name}{" "}
      <span className="text-sm text-content-secondary">{details.join(" · ")}</span>
    </span>
  );
}

function MergePanel({
  researcher,
  units,
  onClose,
}: {
  researcher: Researcher;
  units: Unit[];
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [error, setError] = useState<unknown>(null);
  const targets = useRecordSearch(search, researcher.id);

  async function merge(target: Researcher): Promise<void> {
    setError(null);
    try {
      await http.post(`/researchers/${researcher.id}/merge`, { into_id: target.id });
      await queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast({
        text: t("researchers.merged", { from: researcher.name, to: target.name }),
        undo: () =>
          void http
            .post(`/researchers/${researcher.id}/unmerge`, {})
            .then(async () => {
              await queryClient.invalidateQueries({ queryKey: QUERY_KEY });
              toast({ text: t("researchers.merge_undone") });
            })
            .catch((failure: unknown) => toast({ text: errorMessage(t, failure) })),
      });
      onClose();
    } catch (failure) {
      setError(failure);
    }
  }

  return (
    <SidePanel title={t("researchers.merge_into", { name: researcher.name })} onClose={onClose}>
      <input
        className="input"
        autoFocus
        aria-label={t("researchers.search")}
        placeholder={t("researchers.search")}
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />
      <p className="field-hint">{t("researchers.merge_hint")}</p>
      <ul className="mt-4xs space-y-4xs">
        {targets.map((target) => (
          <li key={target.id} className="flex flex-wrap items-center justify-between gap-4xs">
            <RecordSummary record={target} units={units} />
            <button type="button" className="btn-small" onClick={() => void merge(target)}>
              {t("researchers.merge_choose")}
            </button>
          </li>
        ))}
      </ul>
      {error !== null && (
        <p role="alert" className="field-error">
          {errorMessage(t, error)}
        </p>
      )}
    </SidePanel>
  );
}

function releaseLabel(t: TFunction, release: ResearcherRelease): string {
  return [
    release.code ?? t("researchers.no_code"),
    release.release_date,
    release.title ?? release.paper_title ?? t("researchers.no_title"),
  ]
    .filter(Boolean)
    .join(" · ");
}

function SplitPanel({
  researcher,
  units,
  onClose,
}: {
  researcher: Researcher;
  units: Unit[];
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const { timezone } = useBrand();
  const { data: detail } = useQuery({
    queryKey: ["researchers", "detail", researcher.id],
    queryFn: () => http.get<ResearcherDetail>(`/researchers/${researcher.id}`),
  });
  const [chosen, setChosen] = useState<ReadonlySet<string>>(new Set());
  const [toNew, setToNew] = useState(true);
  const [name, setName] = useState(researcher.name);
  const [notes, setNotes] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<unknown>(null);
  const targets = useRecordSearch(search, researcher.id);

  function toggle(id: string): void {
    setChosen((current) => {
      const next = new Set(current);
      if (!next.delete(id)) next.add(id);
      return next;
    });
  }

  async function undoSplit(result: SplitResult, releaseIds: string[]): Promise<void> {
    await http.post(`/researchers/${result.target.id}/split`, {
      release_ids: releaseIds,
      into_id: result.source.id,
    });
    // A record made just for this goes away again, so the Undo leaves no trace.
    if (result.created) await http.delete(`/researchers/${result.target.id}`);
    await queryClient.invalidateQueries({ queryKey: QUERY_KEY });
  }

  async function move(into?: Researcher): Promise<void> {
    setError(null);
    const releaseIds = [...chosen];
    try {
      const result = await http.post<SplitResult>(`/researchers/${researcher.id}/split`, {
        release_ids: releaseIds,
        ...(into ? { into_id: into.id } : { name, notes: notes || null }),
      });
      await queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast({
        text: t("researchers.split_done", { count: releaseIds.length, name: result.target.name }),
        undo: () =>
          void undoSplit(result, releaseIds).catch((failure: unknown) =>
            toast({ text: errorMessage(t, failure) }),
          ),
      });
      onClose();
    } catch (failure) {
      setError(failure);
    }
  }

  async function unmerge(id: string, recordName: string): Promise<void> {
    setError(null);
    try {
      await http.post(`/researchers/${id}/unmerge`, {});
      await queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast({ text: t("researchers.unmerged", { name: recordName }) });
    } catch (failure) {
      setError(failure);
    }
  }

  const releases = detail?.releases ?? [];
  const merged = detail?.merged_records ?? [];

  return (
    <SidePanel title={t("researchers.split_title", { name: researcher.name })} onClose={onClose}>
      <p className="field-hint">{t("researchers.split_hint")}</p>
      {detail && releases.length === 0 && (
        <p className="mt-4xs text-content-secondary">{t("researchers.split_none")}</p>
      )}
      <ul className="mt-4xs space-y-5xs">
        {releases.map((release) => (
          <li key={release.id}>
            <label className="inline-flex items-start gap-5xs">
              <input
                type="checkbox"
                className="mt-1"
                checked={chosen.has(release.id)}
                onChange={() => toggle(release.id)}
              />
              <span>{releaseLabel(t, release)}</span>
            </label>
          </li>
        ))}
      </ul>

      {chosen.size > 0 && (
        <fieldset className="mt-3xs">
          <legend className="field-label">{t("researchers.split_target")}</legend>
          <div className="flex flex-wrap gap-3xs">
            <label className="inline-flex items-center gap-5xs">
              <input type="radio" checked={toNew} onChange={() => setToNew(true)} />
              {t("researchers.split_new")}
            </label>
            <label className="inline-flex items-center gap-5xs">
              <input type="radio" checked={!toNew} onChange={() => setToNew(false)} />
              {t("researchers.split_existing")}
            </label>
          </div>
          {toNew ? (
            <div className="mt-4xs space-y-4xs">
              <div>
                <label className="field-label" htmlFor={`split-name-${researcher.id}`}>
                  {t("researchers.split_new_name")}
                </label>
                <input
                  id={`split-name-${researcher.id}`}
                  className="input"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </div>
              <div>
                <label className="field-label" htmlFor={`split-notes-${researcher.id}`}>
                  {t("researchers.split_new_notes")}
                </label>
                <input
                  id={`split-notes-${researcher.id}`}
                  className="input"
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                />
              </div>
              <button type="button" className="btn-small" onClick={() => void move()}>
                {t("researchers.split_move", { count: chosen.size })}
              </button>
            </div>
          ) : (
            <div className="mt-4xs">
              <input
                className="input"
                aria-label={t("researchers.search")}
                placeholder={t("researchers.search")}
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
              <ul className="mt-4xs space-y-4xs">
                {targets.map((target) => (
                  <li
                    key={target.id}
                    className="flex flex-wrap items-center justify-between gap-4xs"
                  >
                    <RecordSummary record={target} units={units} />
                    <button type="button" className="btn-small" onClick={() => void move(target)}>
                      {t("researchers.split_move", { count: chosen.size })}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </fieldset>
      )}

      {merged.length > 0 && (
        <div className="mt-2xs">
          <p className="field-label">{t("researchers.merged_title")}</p>
          <ul className="space-y-4xs">
            {merged.map((record) => (
              <li key={record.id} className="flex flex-wrap items-center justify-between gap-4xs">
                <span>
                  {t("researchers.merged_entry", {
                    name: record.name,
                    date: formatDate(record.updated_at, timezone),
                    count: record.release_count,
                  })}
                </span>
                <button
                  type="button"
                  className="btn-small"
                  onClick={() => void unmerge(record.id, record.name)}
                >
                  {t("researchers.unmerge")}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {error !== null && (
        <p role="alert" className="field-error">
          {errorMessage(t, error)}
        </p>
      )}
    </SidePanel>
  );
}

function ResearcherRow({
  researcher,
  units,
  canEdit,
  onShowNamesakes,
  onOpen,
}: {
  researcher: Researcher;
  units: Unit[];
  canEdit: boolean;
  onShowNamesakes: (name: string) => void;
  onOpen: (kind: PanelKind) => void;
}) {
  const { t, i18n } = useTranslation();
  const saver = useFieldSaver(`/researchers/${researcher.id}`, QUERY_KEY);
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
          {researcher.same_name_count > 0 && (
            <button
              type="button"
              className="chip mt-5xs"
              onClick={() => onShowNamesakes(researcher.name)}
            >
              {t("researchers.same_name", { count: researcher.same_name_count })}
            </button>
          )}
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
        <td className="min-w-36">
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
        <td className="min-w-52">
          <TextField
            label={t("researchers.notes")}
            title={t("researchers.notes_hint")}
            value={researcher.notes}
            version={versions.notes}
            save={saver("notes")}
            disabled={!canEdit}
          />
        </td>
        <td className="text-center">{researcher.release_count}</td>
        <td className="pinned-right">
          {canEdit && (
            <div className="flex gap-5xs">
              <button type="button" className="btn-small" onClick={() => onOpen("merge")}>
                {t("researchers.merge")}
              </button>
              {(researcher.release_count > 0 || researcher.merged_count > 0) && (
                <button type="button" className="btn-small" onClick={() => onOpen("split")}>
                  {t("researchers.split")}
                </button>
              )}
            </div>
          )}
        </td>
      </tr>
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
  const [sameName, setSameName] = useState(false);
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [panel, setPanel] = useState<{ kind: PanelKind; researcher: Researcher } | null>(null);
  const term = useDebounced(search, 250);
  const params = new URLSearchParams({ limit: String(limit) });
  if (term.trim()) params.set("search", term.trim());
  if (status) params.set("status", status);
  if (sameName) params.set("same_name", "true");

  const { data } = useQuery({
    queryKey: [...QUERY_KEY, term, status, sameName, limit],
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
        <label className="inline-flex items-center gap-5xs">
          <input
            type="checkbox"
            checked={sameName}
            onChange={(event) => {
              setSameName(event.target.checked);
              setLimit(PAGE_SIZE);
            }}
          />
          {t("researchers.same_name_only")}
        </label>
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
              <th title={t("researchers.notes_hint")}>{t("researchers.notes")}</th>
              <th>{t("researchers.releases")}</th>
              <th className="pinned-right">{t("common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {(data?.items ?? []).map((researcher) => (
              <ResearcherRow
                key={researcher.id}
                researcher={researcher}
                units={units ?? []}
                canEdit={canEdit}
                onShowNamesakes={(name) => {
                  setSearch(name);
                  setLimit(PAGE_SIZE);
                }}
                onOpen={(kind) => setPanel({ kind, researcher })}
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
      {panel?.kind === "merge" && (
        <MergePanel
          key={panel.researcher.id}
          researcher={panel.researcher}
          units={units ?? []}
          onClose={() => setPanel(null)}
        />
      )}
      {panel?.kind === "split" && (
        <SplitPanel
          key={panel.researcher.id}
          researcher={panel.researcher}
          units={units ?? []}
          onClose={() => setPanel(null)}
        />
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

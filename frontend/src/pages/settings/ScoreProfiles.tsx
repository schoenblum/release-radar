import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { http } from "../../api/client";
import { errorMessage } from "../../api/errors";
import type {
  Institution,
  PreviewRow,
  ProfilePreview,
  ReleaseType,
  ScoreComponent,
  ScoreProfile,
  ScoreProfileDraft,
  ScoreProfileVersion,
} from "../../api/types";
import { useBrand } from "../../brand";
import { useToast } from "../../components/Toast";
import { formatDateTime } from "../../dates";
import { headingId } from "../Manual";
import { SectionHeader, SubHeading } from "./SettingsLayout";

const PROFILES = ["score-profiles"];
const INSTITUTION = ["settings", "institution"];
const NEW = "new";

/** Weights as typed: a number, or empty while someone is typing. */
type Weights = Record<string, number | "">;
interface Draft extends Omit<ScoreProfileDraft, "weights"> {
  weights: Weights;
}

function draftOf(version: ScoreProfileVersion | ScoreProfileDraft, name?: string): Draft {
  return {
    name_en: name ?? version.name_en,
    name_ja: version.name_ja,
    purpose: version.purpose,
    weights: { ...version.weights },
    altmetric_basis: version.altmetric_basis,
    coverage_min: version.coverage_min,
    comparison_years: version.comparison_years,
    min_values: version.min_values,
  };
}

function toSave(draft: Draft): ScoreProfileDraft {
  const weights: Record<string, number> = {};
  for (const [key, weight] of Object.entries(draft.weights)) {
    if (typeof weight === "number" && weight > 0) weights[key] = weight;
  }
  return { ...draft, weights };
}

function total(weights: Weights): number {
  return Object.values(weights).reduce<number>(
    (sum, weight) => sum + (typeof weight === "number" ? weight : 0),
    0,
  );
}

// The unsaved draft survives a reload (phase-2 brief §4.3), in this browser only.
const storageKey = (id: string) => `rr.score-profile-draft.${id}`;

function loadDraft(id: string): { base: number; draft: Draft } | null {
  try {
    const text = window.localStorage.getItem(storageKey(id));
    return text ? (JSON.parse(text) as { base: number; draft: Draft }) : null;
  } catch {
    return null;
  }
}

function keepDraft(id: string, base: number, draft: Draft | null): void {
  try {
    if (draft) window.localStorage.setItem(storageKey(id), JSON.stringify({ base, draft }));
    else window.localStorage.removeItem(storageKey(id));
  } catch {
    // Private browsing: the draft then lasts as long as the page.
  }
}

/** The text after typing in a number field: a whole number, or empty. */
function wholeNumber(text: string): number | "" {
  if (text.trim() === "") return "";
  const number = Number(text);
  return Number.isFinite(number) ? Math.round(number) : "";
}

function TopFive({ title, rows }: { title: string; rows: PreviewRow[] | null | undefined }) {
  const { t } = useTranslation();
  return (
    <div className="min-w-0 flex-1">
      <h4 className="mb-4xs font-semibold">{title}</h4>
      {!rows ? (
        <p className="text-sm text-content-secondary">…</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-content-secondary">{t("settings.profiles.preview_none")}</p>
      ) : (
        <ol className="list-decimal pl-3xs text-sm">
          {rows.map((row) => (
            <li key={row.release_id} className="mb-5xs">
              <Link to={`/data?view=all&release=${row.release_id}`}>
                {row.code ?? "—"} {row.title ?? t("data.no_title")}
              </Link>{" "}
              <span className="tabular-nums text-content-secondary">
                {t("settings.profiles.preview_score", {
                  score: row.score,
                  coverage: Math.round(row.coverage * 100),
                })}
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function History({ profile, components }: { profile: ScoreProfile; components: ScoreComponent[] }) {
  const { t, i18n } = useTranslation();
  const { timezone } = useBrand();
  const label = (key: string) => {
    const found = components.find((item) => item.key === key);
    return found ? (i18n.language === "ja" ? found.label_ja : found.label_en) : key;
  };
  return (
    <details className="mt-xs">
      <summary className="cursor-pointer font-semibold">
        {t("settings.profiles.history", { count: profile.versions.length })}
      </summary>
      <div className="table-scroll mt-4xs">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("settings.profiles.version")}</th>
              <th>{t("settings.profiles.saved_when")}</th>
              <th>{t("settings.profiles.saved_by")}</th>
              <th>{t("settings.profiles.weights")}</th>
              <th>{t("settings.profiles.rules")}</th>
            </tr>
          </thead>
          <tbody>
            {profile.versions.map((version) => (
              <tr key={version.id}>
                <td>{version.version}</td>
                <td className="whitespace-nowrap">
                  {formatDateTime(version.created_at, timezone)}
                </td>
                <td>{version.created_by ?? t("settings.profiles.system")}</td>
                <td className="text-sm">
                  {Object.entries(version.weights)
                    .map(([key, weight]) => `${label(key)} ${weight}`)
                    .join(" · ")}
                </td>
                <td className="text-sm">
                  {t("settings.profiles.rules_summary", {
                    basis: t(`settings.profiles.basis_${version.altmetric_basis}`),
                    coverage: version.coverage_min,
                    years: version.comparison_years,
                    values: version.min_values,
                  })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

function Editor({
  profile,
  start,
  components,
  onSaved,
  onDuplicate,
}: {
  /** Null while making a new profile. */
  profile: ScoreProfile | null;
  start: Draft;
  components: ScoreComponent[];
  onSaved: (profile: ScoreProfile) => void;
  onDuplicate: () => void;
}) {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const id = profile?.id ?? NEW;
  const base = profile?.current.version ?? 0;
  const [draft, setDraft] = useState<Draft>(() => {
    const kept = loadDraft(id);
    return kept && kept.base === base ? kept.draft : start;
  });
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);
  const [previewed, setPreviewed] = useState(draft);
  const dirty = JSON.stringify(draft) !== JSON.stringify(start);
  const sum = total(draft.weights);
  const ready = sum === 100 && draft.name_en.trim() !== "";

  useEffect(() => keepDraft(id, base, dirty ? draft : null), [id, base, dirty, draft]);
  // The preview follows the draft once typing pauses.
  useEffect(() => {
    const timer = window.setTimeout(() => setPreviewed(draft), 400);
    return () => window.clearTimeout(timer);
  }, [draft]);
  const previewReady = total(previewed.weights) === 100;
  const { data: preview } = useQuery({
    queryKey: ["score-profiles", "preview", id, JSON.stringify(toSave(previewed))],
    queryFn: () =>
      http.post<ProfilePreview>("/score-profiles/preview", {
        version: { ...toSave(previewed), name_en: previewed.name_en.trim() || "—" },
        profile_id: profile?.id ?? null,
      }),
    enabled: previewReady,
    placeholderData: keepPreviousData,
  });

  const change = (changes: Partial<Draft>) => setDraft({ ...draft, ...changes });
  const isJa = i18n.language === "ja";

  async function save(): Promise<void> {
    setError(null);
    setSaving(true);
    try {
      const body = toSave(draft);
      const saved = profile
        ? await http.post<ScoreProfile>(`/score-profiles/${profile.id}/versions`, body)
        : await http.post<ScoreProfile>("/score-profiles", body);
      keepDraft(id, base, null);
      await queryClient.invalidateQueries({ queryKey: PROFILES });
      toast({ text: t("settings.profiles.saved", { version: saved.current.version }) });
      onSaved(saved);
    } catch (failure) {
      setError(failure);
    } finally {
      setSaving(false);
    }
  }

  async function makeDefault(): Promise<void> {
    if (!profile) return;
    setError(null);
    try {
      await http.post(`/score-profiles/${profile.id}/default`);
      await queryClient.invalidateQueries({ queryKey: PROFILES });
      toast({ text: t("settings.profiles.now_default") });
    } catch (failure) {
      setError(failure);
    }
  }

  return (
    <section className="max-w-4xl" aria-label={draft.name_en || t("settings.profiles.new")}>
      <div className="grid gap-2xs sm:grid-cols-2">
        <div>
          <label className="field-label" htmlFor="profile-name-en">
            {t("settings.profiles.name_en")}
          </label>
          <input
            id="profile-name-en"
            className="input"
            value={draft.name_en}
            onChange={(event) => change({ name_en: event.target.value })}
          />
        </div>
        <div>
          <label className="field-label" htmlFor="profile-name-ja">
            {t("settings.profiles.name_ja")}
          </label>
          <input
            id="profile-name-ja"
            className="input"
            value={draft.name_ja ?? ""}
            onChange={(event) => change({ name_ja: event.target.value || null })}
          />
        </div>
        <div className="sm:col-span-2">
          <label className="field-label" htmlFor="profile-purpose">
            {t("settings.profiles.purpose")}
          </label>
          <textarea
            id="profile-purpose"
            className="input"
            rows={2}
            value={draft.purpose ?? ""}
            onChange={(event) => change({ purpose: event.target.value || null })}
          />
        </div>
      </div>

      <fieldset className="mt-xs">
        <legend className="field-label">{t("settings.profiles.weights")}</legend>
        <p className="mb-4xs text-sm text-content-secondary">
          {t("settings.profiles.weights_help")}
        </p>
        <div className="grid max-w-2xl gap-y-5xs">
          {components.map((component) => {
            const barred = profile?.seeded === true && !component.allowed_in_default;
            const inputId = `weight-${component.key}`;
            return (
              <div key={component.key} className="flex items-center gap-4xs">
                <label htmlFor={inputId} className="flex-1">
                  {isJa ? component.label_ja : component.label_en}
                  {barred && (
                    <span className="block text-sm text-content-secondary">
                      {t("settings.profiles.not_in_default")}
                    </span>
                  )}
                </label>
                <input
                  id={inputId}
                  className="input w-24 text-right tabular-nums"
                  type="number"
                  min={0}
                  max={100}
                  step={1}
                  disabled={barred}
                  value={draft.weights[component.key] ?? ""}
                  onChange={(event) =>
                    change({
                      weights: {
                        ...draft.weights,
                        [component.key]: wholeNumber(event.target.value),
                      },
                    })
                  }
                />
              </div>
            );
          })}
        </div>
        <p role="status" className="mt-4xs font-semibold tabular-nums">
          {t("settings.profiles.total", { total: sum })}
          {sum !== 100 && (
            <span className="block text-sm font-normal text-content-secondary">
              {t("settings.profiles.total_needed")}
            </span>
          )}
        </p>
      </fieldset>

      <div className="mt-xs grid gap-2xs sm:grid-cols-2">
        <fieldset>
          <legend className="field-label">{t("settings.profiles.basis")}</legend>
          {(["increase", "d28"] as const).map((basis) => (
            <label key={basis} className="mb-5xs flex items-center gap-4xs">
              <input
                type="radio"
                name="altmetric-basis"
                checked={draft.altmetric_basis === basis}
                onChange={() => change({ altmetric_basis: basis })}
              />
              {t(`settings.profiles.basis_${basis}`)}
            </label>
          ))}
        </fieldset>
        <div className="grid gap-4xs">
          {(
            [
              ["coverage_min", 0, 100],
              ["comparison_years", 1, 10],
              ["min_values", 1, 1000],
            ] as const
          ).map(([name, min, max]) => (
            <div key={name}>
              <label className="field-label" htmlFor={`profile-${name}`}>
                {t(`settings.profiles.${name}`)}
              </label>
              <input
                id={`profile-${name}`}
                className="input w-28 tabular-nums"
                type="number"
                min={min}
                max={max}
                value={draft[name]}
                onChange={(event) => {
                  const value = wholeNumber(event.target.value);
                  change({ [name]: value === "" ? min : Math.min(max, Math.max(min, value)) });
                }}
              />
              <p className="field-hint">{t(`settings.profiles.${name}_hint`)}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-xs flex flex-wrap items-center gap-4xs">
        <button
          type="button"
          className="btn-primary"
          disabled={!dirty || !ready || saving}
          onClick={() => void save()}
        >
          {profile ? t("settings.profiles.save") : t("settings.profiles.create")}
        </button>
        {dirty && (
          <button type="button" className="btn-quiet" onClick={() => setDraft(start)}>
            {t("settings.profiles.discard")}
          </button>
        )}
        {profile && (
          <button type="button" className="btn-quiet" onClick={onDuplicate}>
            {t("settings.profiles.duplicate")}
          </button>
        )}
        {profile && !profile.is_default && (
          <button type="button" className="btn-quiet" onClick={() => void makeDefault()}>
            {t("settings.profiles.make_default")}
          </button>
        )}
        {profile && (
          <span className="text-sm text-content-secondary">
            {dirty
              ? t("settings.profiles.unsaved", { version: profile.current.version })
              : t("settings.profiles.at_version", { version: profile.current.version })}
          </span>
        )}
      </div>
      {error !== null && (
        <p role="alert" className="notice-error mt-3xs">
          {errorMessage(t, error)}
        </p>
      )}

      <h3 className="mb-4xs mt-xs text-xl">{t("settings.profiles.preview")}</h3>
      <p className="mb-4xs max-w-3xl text-sm text-content-secondary">
        {t("settings.profiles.preview_help")}
      </p>
      <div className="flex flex-col gap-2xs sm:flex-row">
        {profile && (
          <TopFive
            title={t("settings.profiles.preview_saved", { version: profile.current.version })}
            rows={preview?.saved}
          />
        )}
        <TopFive
          title={t("settings.profiles.preview_edited")}
          rows={previewReady ? preview?.edited : []}
        />
      </div>
      {profile && <History profile={profile} components={components} />}
    </section>
  );
}

/** Where the two Analysis filters start (R6.4.2): release types, saved as they are ticked. */
function AnalysisDefaults() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const [error, setError] = useState<unknown>(null);
  const { data: institution } = useQuery({
    queryKey: INSTITUTION,
    queryFn: () => http.get<Institution>("/settings/institution"),
  });
  const { data: types = [] } = useQuery({
    queryKey: ["lists", "release_types"],
    queryFn: () => http.get<ReleaseType[]>("/lists/release_types"),
  });
  if (!institution) return null;
  const isJa = i18n.language === "ja";
  const analysed = institution.analysed_release_type_ids ?? [];
  const shown = institution.shown_release_type_ids ?? [];
  const active = types.filter((type) => type.is_active).sort((a, b) => a.position - b.position);

  async function toggle(field: "analysed_release_type_ids" | "shown_release_type_ids", id: string) {
    setError(null);
    const current = field === "analysed_release_type_ids" ? analysed : shown;
    const next = current.includes(id) ? current.filter((item) => item !== id) : [...current, id];
    try {
      await http.patchField(
        "/settings/institution",
        field,
        next,
        institution!.field_versions[field] ?? 0,
      );
    } catch (failure) {
      setError(failure);
    }
    await queryClient.invalidateQueries({ queryKey: INSTITUTION });
  }

  const group = (field: "analysed_release_type_ids" | "shown_release_type_ids") => {
    const chosen = field === "analysed_release_type_ids" ? analysed : shown;
    return (
      <fieldset className="min-w-0 flex-1">
        <legend className="field-label">{t(`settings.profiles.defaults_${field}`)}</legend>
        {active.map((type) => {
          const outside =
            field === "shown_release_type_ids" &&
            analysed.length > 0 &&
            !analysed.includes(type.id);
          return (
            <label key={type.id} className="mb-5xs flex items-center gap-4xs">
              <input
                type="checkbox"
                checked={chosen.includes(type.id)}
                disabled={outside}
                onChange={() => void toggle(field, type.id)}
              />
              <span className={outside ? "text-content-secondary" : undefined}>
                {(isJa && type.name_ja) || type.name_en}
              </span>
            </label>
          );
        })}
      </fieldset>
    );
  };

  return (
    <div className="max-w-3xl">
      <p className="mb-3xs text-content-secondary">{t("settings.profiles.defaults_help")}</p>
      <div className="flex flex-col gap-2xs sm:flex-row">
        {group("analysed_release_type_ids")}
        {group("shown_release_type_ids")}
      </div>
      {error !== null && (
        <p role="alert" className="notice-error mt-3xs">
          {errorMessage(t, error)}
        </p>
      )}
    </div>
  );
}

/** Settings → Score profiles (R8.2, R8.2.5, phase-2 brief §4.3), admins only. */
export default function ScoreProfilesSettings() {
  const { t, i18n } = useTranslation();
  const [selected, setSelected] = useState<string | null>(null);
  // A new profile starts from the selected one (duplicate) or from the default.
  const [making, setMaking] = useState<Draft | null>(null);
  const { data: profiles } = useQuery({
    queryKey: PROFILES,
    queryFn: () => http.get<ScoreProfile[]>("/score-profiles"),
  });
  const { data: components = [] } = useQuery({
    queryKey: ["score-profiles", "components"],
    queryFn: () => http.get<ScoreComponent[]>("/score-profiles/components"),
  });
  const current = selected ?? profiles?.find((item) => item.is_default)?.id ?? null;
  const { data: profile } = useQuery({
    queryKey: [...PROFILES, current],
    queryFn: () => http.get<ScoreProfile>(`/score-profiles/${current}`),
    enabled: current !== null && making === null,
  });
  const start = useMemo(() => (profile ? draftOf(profile.current) : null), [profile]);
  if (!profiles) return null;
  const isJa = i18n.language === "ja";
  const nameOf = (version: ScoreProfileVersion) => (isJa && version.name_ja) || version.name_en;

  function startNew(from: ScoreProfileVersion, copy: boolean): void {
    keepDraft(NEW, 0, null);
    setMaking(draftOf(from, copy ? t("settings.profiles.copy_of", { name: from.name_en }) : ""));
  }

  return (
    <div>
      <SectionHeader
        title={t("settings.sections.score_profiles")}
        help={t("settings.help.score_profiles")}
      />
      <p className="mb-3xs max-w-3xl text-sm">
        <Link to={`/manual#${headingId(t("settings.profiles.manual_heading"))}`}>
          {t("settings.profiles.manual")}
        </Link>
      </p>
      <nav aria-label={t("settings.profiles.list")} className="mb-2xs flex flex-wrap gap-4xs">
        {profiles.map((item) => (
          <button
            key={item.id}
            type="button"
            aria-current={making === null && item.id === current ? "true" : undefined}
            className={
              making === null && item.id === current ? "btn-small nav-link-active" : "btn-small"
            }
            onClick={() => {
              setMaking(null);
              setSelected(item.id);
            }}
          >
            {nameOf(item.current)}
            {item.is_default && ` · ${t("settings.profiles.default")}`}
          </button>
        ))}
        <button
          type="button"
          className="btn-small"
          onClick={() => {
            const base = profiles.find((item) => item.is_default) ?? profiles[0];
            if (base) startNew(base.current, false);
          }}
        >
          {t("settings.profiles.new")}
        </button>
      </nav>

      {making !== null ? (
        <Editor
          key="new"
          profile={null}
          start={making}
          components={components}
          onSaved={(saved) => {
            setMaking(null);
            setSelected(saved.id);
          }}
          onDuplicate={() => undefined}
        />
      ) : (
        profile &&
        start && (
          <Editor
            key={`${profile.id}-${profile.current.version}`}
            profile={profile}
            start={start}
            components={components}
            onSaved={(saved) => setSelected(saved.id)}
            onDuplicate={() => startNew(profile.current, true)}
          />
        )
      )}

      <SubHeading>{t("settings.profiles.defaults_title")}</SubHeading>
      <AnalysisDefaults />
    </div>
  );
}

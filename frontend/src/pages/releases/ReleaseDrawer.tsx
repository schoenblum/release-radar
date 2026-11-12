import { Fragment, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { http } from "../../api/client";
import { errorMessage } from "../../api/errors";
import type {
  Author,
  CrossrefStatus,
  CustomField,
  HistoryEntry,
  Measure,
  Reading,
  Release,
  ReleaseSaved,
} from "../../api/types";
import { useBrand } from "../../brand";
import ConfirmButton from "../../components/ConfirmButton";
import { SelectField, TextField, ToggleField } from "../../components/fields/Autosave";
import SidePanel from "../../components/SidePanel";
import { useToast } from "../../components/Toast";
import { formatDateTime } from "../../dates";
import { translate } from "../../i18n";
import { inOtherZones, shortLabel, zoneName } from "../../timeZones";
import {
  customColumnId,
  customOptions,
  customValueText,
  linkFor,
  type GridContext,
} from "./columns";
import { GENDERS } from "./gender";
import { normaliseDate } from "./parse";
import { releaseDateValue, releaseTimeValue, shownTime } from "./releaseMoment";
import ResearcherFeedback from "./ResearcherFeedback";
import ResearcherPicker from "./ResearcherPicker";
import { useReleaseActions, useReleaseHistory } from "./useReleaseData";

// Grouped here for reading; within a section they follow the order set in Settings.
const RELEASE_SECTION = new Set([
  "title",
  "title_ja",
  "writer",
  "researcher",
  "researcher_gender",
  "also_featured",
  "unit",
  "field",
  "release_type",
  "embargoed",
  "release_date",
  "release_time",
  "ea_url",
  "website_url",
  "ea_top_page",
  "ea_top_position",
]);
const PAPER_SECTION = new Set(["doi", "journal", "paper_title", "publication_date", "authors"]);

function authorName(author: Author): string {
  return author.name ?? [author.given, author.family].filter(Boolean).join(" ");
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="drawer-section">
      <h3 className="drawer-heading">{title}</h3>
      {children}
    </section>
  );
}

function Labelled({
  id,
  label,
  required = false,
  href,
  children,
}: {
  id: string;
  label: string;
  required?: boolean;
  /** A saved link, opened in a new tab from beside the label. */
  href?: string | null;
  children: React.ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <div className="drawer-field">
      <div className="flex items-baseline justify-between gap-4xs">
        <label className="field-label" htmlFor={id}>
          {label}
          {required && <span aria-hidden="true"> *</span>}
        </label>
        {href && (
          <a
            className="drawer-link"
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={t("data.open_link", { field: label })}
          >
            {t("data.open")}
            <span aria-hidden="true"> ↗</span>
          </a>
        )}
      </div>
      {children}
    </div>
  );
}

function ReadingRow({
  release,
  reading,
  measure,
  context,
}: {
  release: Release;
  reading: Reading;
  measure: Measure;
  context: GridContext;
}) {
  const { t, i18n } = useTranslation();
  const actions = useReleaseActions();
  const [error, setError] = useState<unknown>(null);
  const label = (i18n.language === "ja" && measure.label_ja) || measure.label_en;
  const locked = measure.source === "derived" || !context.canEdit;
  const id = `reading-${reading.id}`;

  async function send(body: Record<string, unknown>, version: number): Promise<Reading> {
    const saved = await http.patch<Reading>(`/readings/${reading.id}`, { ...body, version });
    actions.storeReading(release.id, saved);
    actions.refreshDue();
    return saved;
  }

  async function setState(state: "not_applicable" | "missing"): Promise<void> {
    setError(null);
    try {
      await send({ state }, reading.version);
    } catch (failure) {
      setError(failure);
    }
  }

  const isNa = reading.display_state === "not_applicable";
  // Fetched by a job (R8.1.1). A number typed here wins, and the job leaves it alone.
  const fetched = measure.source === "ga4";
  return (
    <div className="drawer-reading">
      <Labelled id={id} label={label}>
        <TextField
          id={id}
          label={label}
          className="input"
          value={reading.value}
          version={reading.version}
          disabled={locked}
          placeholder={isNa ? t("data.not_applicable") : undefined}
          save={async (value, version) => {
            const saved = await send({ value }, version);
            return { value: saved.value, version: saved.version };
          }}
        />
      </Labelled>
      <div className="drawer-reading-side">
        <p className="text-sm text-content-secondary">
          {reading.inferred
            ? t("data.inferred_state")
            : t(`data.reading_states.${reading.display_state}`)}
          {fetched && reading.state === "value"
            ? ` · ${t(reading.source === "auto" ? "data.from_ga4" : "data.typed_over_ga4")}`
            : ""}
          {reading.due_date ? ` · ${t("data.due_on", { date: reading.due_date })}` : ""}
        </p>
        {!locked &&
          (isNa ? (
            <button type="button" className="btn-small" onClick={() => void setState("missing")}>
              {t("data.clear_na")}
            </button>
          ) : (
            <button
              type="button"
              className="btn-small"
              onClick={() => void setState("not_applicable")}
            >
              {t("data.set_na")}
            </button>
          ))}
        {error !== null && (
          <p role="alert" className="field-error">
            {errorMessage(t, error)}
          </p>
        )}
      </div>
      <TextField
        label={t("data.reading_note", { measure: label })}
        className="input mt-5xs"
        placeholder={t("data.reading_note_placeholder")}
        value={reading.note}
        version={reading.version}
        disabled={locked}
        save={async (note, version) => {
          const saved = await send({ note }, version);
          return { value: saved.note, version: saved.version };
        }}
      />
    </div>
  );
}

function CustomFieldRow({
  release,
  field,
  context,
}: {
  release: Release;
  field: CustomField;
  context: GridContext;
}) {
  const { t, i18n } = useTranslation();
  const actions = useReleaseActions();
  const [error, setError] = useState<unknown>(null);
  const isJa = i18n.language === "ja";
  const baseLabel = (isJa && field.label_ja) || field.label_en;
  const isMine = field.owner_id === context.userId;
  const canEdit =
    context.canEdit && field.is_active && (field.scope === "institution" || isMine);
  const label =
    field.scope === "personal" && !isMine
      ? t("data.owned_by", { label: baseLabel, owner: field.owner_name ?? "" })
      : baseLabel;
  const help = (isJa && field.help_ja) || field.help_en || undefined;
  const name = `custom_values.${field.key}`;
  const version = release.field_versions[name] ?? 0;
  const stored = release.custom_values[field.key];
  const options = customOptions(context, field);
  const id = `${customColumnId(field)}-drawer`;

  async function send(body: Record<string, unknown>, atVersion: number): Promise<unknown> {
    const saved = await http.patch<ReleaseSaved>(
      `/releases/${release.id}/custom/${encodeURIComponent(field.key)}`,
      { ...body, version: atVersion },
    );
    actions.storeRelease(saved.release);
    actions.refreshDue();
    const value = saved.value as { state: string; value?: unknown } | null;
    return { value: value?.value ?? null, version: saved.version };
  }

  async function setState(state: "not_applicable" | "missing"): Promise<void> {
    setError(null);
    try {
      await send({ state }, version);
    } catch (failure) {
      setError(failure);
    }
  }

  const rawValue = stored?.state === "value" ? stored.value : null;
  const isNa = stored?.state === "not_applicable";
  let control: React.ReactNode;
  if (!canEdit) {
    control = (
      <p className="text-sm">
        {isNa ? t("data.not_applicable") : customValueText(stored, options, field) || "—"}
      </p>
    );
  } else if (field.field_type === "boolean") {
    control = (
      <ToggleField
        label={label}
        value={rawValue === true}
        version={version}
        save={(value, atVersion) => send({ value }, atVersion)}
      />
    );
  } else if (field.field_type === "single_select") {
    control = (
      <SelectField
        id={id}
        label={label}
        className="input"
        value={rawValue as string | null}
        version={version}
        emptyLabel={t("common.none")}
        options={options.map(({ value, label: text }) => ({ value, label: text }))}
        save={(value, atVersion) => send(value ? { value } : { state: "missing" }, atVersion)}
      />
    );
  } else if (field.field_type === "multi_select") {
    const chosen = new Set(Array.isArray(rawValue) ? (rawValue as string[]) : []);
    control = (
      <div>
        {options.map((option) => (
          <label key={option.value} className="flex items-center gap-5xs py-5xs">
            <input
              type="checkbox"
              checked={chosen.has(option.value)}
              onChange={(event) => {
                const next = new Set(chosen);
                if (event.target.checked) next.add(option.value);
                else next.delete(option.value);
                setError(null);
                void send(
                  next.size > 0 ? { value: [...next] } : { state: "missing" },
                  version,
                ).catch((failure: unknown) => setError(failure));
              }}
            />
            {option.label}
          </label>
        ))}
      </div>
    );
  } else {
    control = (
      <TextField
        id={id}
        label={label}
        className="input"
        type={field.field_type === "date" ? "date" : "text"}
        multiline={field.field_type === "long_text"}
        value={rawValue as string | number | null}
        version={version}
        placeholder={isNa ? t("data.not_applicable") : undefined}
        save={(value, atVersion) => send(value.trim() ? { value } : { state: "missing" }, atVersion)}
      />
    );
  }

  return (
    <div className="drawer-field">
      <label className="field-label" htmlFor={id}>
        {label}
      </label>
      {control}
      {help && <p className="field-hint">{help}</p>}
      {canEdit && field.field_type !== "boolean" && (
        <button
          type="button"
          className="btn-small mt-5xs"
          onClick={() => void setState(isNa ? "missing" : "not_applicable")}
        >
          {t(isNa ? "data.clear_na" : "data.set_na")}
        </button>
      )}
      {error !== null && (
        <p role="alert" className="field-error">
          {errorMessage(t, error)}
        </p>
      )}
    </div>
  );
}

function History({ release, context }: { release: Release; context: GridContext }) {
  const { t, i18n } = useTranslation();
  const { timezone } = useBrand();
  const { data } = useReleaseHistory(release.id);
  const isJa = i18n.language === "ja";

  const names = useMemo(() => {
    const map = new Map<string, string>();
    context.units.forEach((u) => map.set(u.id, (isJa && u.name_ja) || u.name_en));
    context.fields.forEach((f) => map.set(f.id, (isJa && f.name_ja) || f.name_en));
    context.writers.forEach((w) => map.set(w.id, (isJa && w.display_name_ja) || w.display_name_en));
    context.releaseTypes.forEach((r) => map.set(r.id, (isJa && r.name_ja) || r.name_en));
    return map;
  }, [context.units, context.fields, context.writers, context.releaseTypes, isJa]);

  const CORE_NAMES: Record<string, string> = {
    writer_id: "writer",
    researcher_id: "researcher",
    unit_id: "unit",
    field_id: "field",
    release_type_id: "release_type",
  };

  function fieldLabel(entry: HistoryEntry): string {
    if (entry.entity === "reading") {
      const measure = context.measures.find((row) => row.key === entry.measure_key);
      const name = measure ? (isJa && measure.label_ja) || measure.label_en : entry.measure_key;
      if (entry.field === "note") return t("data.history_note", { measure: name });
      return name ?? "";
    }
    if (entry.field?.startsWith("custom_values.")) {
      const key = entry.field.slice("custom_values.".length);
      const field = context.customFields.find((row) => row.key === key);
      return field ? (isJa && field.label_ja) || field.label_en : key;
    }
    if (entry.field === "deleted_at") return t("data.history_removed");
    const core = CORE_NAMES[entry.field ?? ""] ?? entry.field ?? "";
    return translate(t, `release_fields.${core}`);
  }

  function shown(entry: HistoryEntry, value: unknown, label: string | null): string {
    if (label) return label;
    if (value === null || value === undefined || value === "") return t("conflict.empty");
    if (entry.field === "state" && typeof value === "string") {
      return t(`data.reading_states.${value}`, { defaultValue: value });
    }
    if (typeof value === "boolean") return t(value ? "common.yes" : "common.no");
    if (typeof value === "string" && names.has(value)) return names.get(value) ?? value;
    if (Array.isArray(value)) {
      return value
        .map((item) => (typeof item === "object" ? authorName(item as Author) : String(item)))
        .join(", ");
    }
    if (typeof value === "object") {
      const wrapped = value as { state?: string; value?: unknown };
      if (wrapped.state === "not_applicable") return t("data.not_applicable");
      if (wrapped.state === "value") return String(wrapped.value);
      return JSON.stringify(value);
    }
    return String(value);
  }

  // The state changing with a value says nothing that the value does not.
  const entries = (data ?? []).filter(
    (entry) => entry.action !== "create" && !(entry.entity === "reading" && entry.field === "state"),
  );
  const created = data?.find((entry) => entry.action === "create" && entry.entity === "release");
  const who = (entry: HistoryEntry): string => {
    if (!entry.user_name) return t("data.history_system");
    return entry.user_active === false
      ? `${entry.user_name} (${t("settings.users.former_user")})`
      : entry.user_name;
  };

  return (
    <Section title={t("data.drawer_history")}>
      <ul className="drawer-history">
        {entries.map((entry, index) => (
          <li key={`${entry.at}-${entry.field}-${index}`}>
            <span className="text-content-secondary">
              {formatDateTime(entry.at, timezone)} · {who(entry)}
            </span>
            <br />
            {fieldLabel(entry)}: {shown(entry, entry.old_value, entry.old_label)} →{" "}
            {shown(entry, entry.new_value, entry.new_label)}
          </li>
        ))}
        {created && (
          <li>
            <span className="text-content-secondary">
              {formatDateTime(created.at, timezone)} · {who(created)}
            </span>
            <br />
            {t("data.history_created")}
          </li>
        )}
      </ul>
    </Section>
  );
}

/**
 * The full record (R7.5.3). One scrolling form with headings and no tabs, beside the grid,
 * which stays visible and usable.
 */
export default function ReleaseDrawer({
  release,
  context,
  onClose,
}: {
  release: Release;
  context: GridContext;
  onClose: () => void;
}) {
  const { t, i18n } = useTranslation();
  const actions = useReleaseActions();
  const toast = useToast();
  const [paperStatus, setPaperStatus] = useState<CrossrefStatus | null>(null);
  const [paperError, setPaperError] = useState<unknown>(null);
  const [changingResearcher, setChangingResearcher] = useState(false);
  const [removeError, setRemoveError] = useState<unknown>(null);
  const isJa = i18n.language === "ja";
  const canEdit = context.canEdit;
  const versions = release.field_versions;

  const configs = useMemo(
    () =>
      [...context.coreFields]
        .filter((config) => config.in_record)
        .sort((a, b) => a.position - b.position),
    [context.coreFields],
  );
  const labelOf = (key: string): string => {
    const config = configs.find((row) => row.key === key);
    const custom = isJa ? config?.label_ja : config?.label_en;
    return custom || translate(t, `release_fields.${key}`);
  };
  const isRequired = (key: string): boolean =>
    configs.find((row) => row.key === key)?.required === true;

  // Release date and time are kept in the institution's zone, and can be typed in another
  // (Daniel, 2026-11-12): the choice shows above whichever of the two comes first.
  const local = context.timezone;
  const zoneChoices = [...new Set([local, ...context.displayZones])];
  const [entryZone, setEntryZone] = useState(local);
  const firstMomentKey = configs.find(
    (row) => row.key === "release_date" || row.key === "release_time",
  )?.key;

  function saver(field: string) {
    return async (value: unknown, version: number) => {
      const saved = await http.patch<ReleaseSaved>(`/releases/${release.id}`, {
        field,
        value,
        version,
      });
      actions.storeRelease(saved.release);
      actions.refreshDue();
      return saved;
    };
  }

  async function fetchPaper(overwrite: boolean): Promise<void> {
    setPaperError(null);
    try {
      setPaperStatus(await actions.fetchPaper(release.id, overwrite));
    } catch (failure) {
      setPaperError(failure);
    }
  }

  async function saveDoi(value: string, version: number): Promise<ReleaseSaved> {
    const saved = await saver("doi")(value, version);
    // A new DOI fills in what is still empty, and never overwrites what someone typed.
    if (saved.value) void fetchPaper(false);
    return saved;
  }

  async function remove(): Promise<void> {
    setRemoveError(null);
    try {
      await actions.remove(release.id);
      onClose();
      toast({
        text: t("data.removed", { name: release.code ?? release.title ?? release.doi ?? "" }),
        undo: () => void actions.restore(release.id),
      });
    } catch (failure) {
      setRemoveError(failure);
    }
  }

  async function pickResearcher(record: { id: string; name: string } | null): Promise<void> {
    setChangingResearcher(false);
    try {
      await saver("researcher_id")(record?.id ?? null, versions.researcher_id ?? 0);
    } catch (failure) {
      setRemoveError(failure);
    }
  }

  const text = (
    key: string,
    attribute: string,
    options: { type?: "text" | "date"; multiline?: boolean; clean?: (value: string) => string } = {},
  ) => {
    const id = `drawer-${key}`;
    const save = saver(attribute);
    const value = (release as unknown as Record<string, string | number | null>)[attribute];
    const href = key === "ea_url" || key === "website_url" ? linkFor(key, release) : null;
    return (
      <Labelled key={key} id={id} label={labelOf(key)} required={isRequired(key)} href={href}>
        <TextField
          id={id}
          label={labelOf(key)}
          className="input"
          type={options.type ?? "text"}
          multiline={options.multiline}
          value={value}
          version={versions[attribute]}
          disabled={!canEdit}
          save={(next, version) => save(options.clean ? options.clean(next) : next, version)}
        />
      </Labelled>
    );
  };

  const select = (
    key: string,
    attribute: string,
    rows: { id: string; label: string; active: boolean }[],
  ) => {
    const id = `drawer-${key}`;
    const current = (release as unknown as Record<string, string | null>)[attribute];
    return (
      <Labelled key={key} id={id} label={labelOf(key)} required={isRequired(key)}>
        <SelectField
          id={id}
          label={labelOf(key)}
          className="input"
          value={current}
          version={versions[attribute]}
          disabled={!canEdit}
          emptyLabel={t("common.none")}
          options={rows
            .filter((row) => row.active || row.id === current)
            .map((row) => ({ value: row.id, label: row.label }))}
          save={saver(attribute)}
        />
      </Labelled>
    );
  };

  const toggle = (key: string, attribute: string, value: boolean) => (
    <div key={key} className="drawer-field">
      <ToggleField
        label={labelOf(key)}
        value={value}
        version={versions[attribute]}
        disabled={!canEdit}
        save={saver(attribute)}
      >
        {labelOf(key)}
      </ToggleField>
    </div>
  );

  const warning = (code: string) =>
    release.warnings.includes(code as never) ? (
      <p key={`${code}-warning`} className="drawer-warning">
        {translate(t, `data.warnings.${code}`)}
      </p>
    ) : null;

  function coreControl(key: string): React.ReactNode {
    switch (key) {
      case "title":
      case "title_ja":
      case "also_featured":
      case "journal":
      case "paper_title":
        return text(key, key);
      case "ea_url":
        return [text(key, key), warning("ea_url_unusual")];
      case "website_url":
        return [text(key, key), warning("website_off_domain")];
      case "doi":
        return (
          <Labelled
            key={key}
            id="drawer-doi"
            label={labelOf(key)}
            required={isRequired(key)}
            href={linkFor("doi", release)}
          >
            <TextField
              id="drawer-doi"
              label={labelOf(key)}
              className="input"
              value={release.doi}
              version={versions.doi}
              disabled={!canEdit}
              save={saveDoi}
            />
            {canEdit && release.doi && (
              <div className="mt-5xs">
                <ConfirmButton
                  label={t("data.refetch")}
                  question={t("data.refetch_question")}
                  onConfirm={() => void fetchPaper(true)}
                />
              </div>
            )}
            {paperStatus && paperStatus !== "found" && (
              <p className="field-hint">{t(`data.crossref_${paperStatus}`)}</p>
            )}
            {paperError !== null && (
              <p role="alert" className="field-error">
                {errorMessage(t, paperError)}
              </p>
            )}
          </Labelled>
        );
      case "writer":
        return select(
          key,
          "writer_id",
          context.writers.map((row) => ({
            id: row.id,
            label: (isJa && row.display_name_ja) || row.display_name_en,
            active: row.is_active,
          })),
        );
      case "unit":
        return select(
          key,
          "unit_id",
          context.units.map((row) => ({
            id: row.id,
            label: (isJa && row.name_ja) || row.name_en,
            active: row.is_active,
          })),
        );
      case "field":
        return select(
          key,
          "field_id",
          context.fields.map((row) => ({
            id: row.id,
            label: (isJa && row.name_ja) || row.name_en,
            active: row.is_active,
          })),
        );
      case "release_type":
        return select(
          key,
          "release_type_id",
          context.releaseTypes.map((row) => ({
            id: row.id,
            label: (isJa && row.name_ja) || row.name_en,
            active: row.is_active,
          })),
        );
      case "researcher":
        return (
          <div key={key} className="drawer-field">
            <p className="field-label">
              {labelOf(key)}
              {isRequired(key) && <span aria-hidden="true"> *</span>}
            </p>
            {changingResearcher ? (
              <div className="relative">
                <ResearcherPicker
                  authors={release.authors}
                  units={context.units}
                  hasValue={release.researcher_id !== null}
                  autoFocus
                  onPick={(record) => void pickResearcher(record)}
                  onClear={() => void pickResearcher(null)}
                  onCancel={() => setChangingResearcher(false)}
                />
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-4xs">
                <span>{release.researcher_name ?? "—"}</span>
                {canEdit && (
                  <button
                    type="button"
                    className="btn-small"
                    onClick={() => setChangingResearcher(true)}
                  >
                    {t("data.change")}
                  </button>
                )}
              </div>
            )}
          </div>
        );
      case "researcher_gender": {
        // The researcher's: a change here shows on all their releases.
        const id = `drawer-${key}`;
        const noResearcher = release.researcher_id === null;
        return (
          <Labelled key={key} id={id} label={labelOf(key)} required={false}>
            <SelectField
              id={id}
              label={labelOf(key)}
              className="input"
              value={release.researcher_gender}
              version={versions.researcher_gender}
              disabled={!canEdit || noResearcher}
              emptyLabel={t("researchers.genders.not_recorded")}
              options={GENDERS.map((gender) => ({
                value: gender,
                label: translate(t, `researchers.genders.${gender}`),
              }))}
              save={saver(key)}
              hint={noResearcher && canEdit ? t("errors.gender_needs_researcher") : undefined}
            />
          </Labelled>
        );
      }
      case "publication_date":
        return text(key, key, { type: "date", clean: normaliseDate });
      case "release_date":
      case "release_time": {
        const id = `drawer-${key}`;
        const isDate = key === "release_date";
        const label = isDate ? labelOf(key) : `${labelOf(key)} (${shortLabel(local)})`;
        const elsewhere = isDate
          ? []
          : inOtherZones(release.release_date, release.release_time, local, context.displayZones);
        const save = saver(key);
        return (
          <Fragment key={key}>
            {key === firstMomentKey && canEdit && zoneChoices.length > 1 && (
              <div className="drawer-field">
                <label className="field-label" htmlFor="drawer-entry-zone">
                  {t("data.entry_zone")}
                </label>
                <select
                  id="drawer-entry-zone"
                  className="input"
                  value={entryZone}
                  onChange={(event) => setEntryZone(event.target.value)}
                >
                  {zoneChoices.map((zone) => (
                    <option key={zone} value={zone}>
                      {zoneName(zone, i18n.language)}
                    </option>
                  ))}
                </select>
                {entryZone !== local && (
                  <p className="field-hint">
                    {t("data.entry_zone_hint", {
                      zone: zoneName(entryZone, i18n.language),
                      local: zoneName(local, i18n.language),
                    })}
                  </p>
                )}
              </div>
            )}
            <Labelled id={id} label={label} required={isRequired(key)}>
              <TextField
                id={id}
                label={label}
                className="input"
                type={isDate ? "date" : "text"}
                value={isDate ? release.release_date : shownTime(release.release_time)}
                version={versions[key]}
                disabled={!canEdit}
                hint={
                  elsewhere.length > 0
                    ? t("data.elsewhere", { times: elsewhere.join(" · ") })
                    : undefined
                }
                save={async (next, version) => {
                  const value = isDate
                    ? releaseDateValue(next, entryZone, local)
                    : releaseTimeValue(next, entryZone, local);
                  const saved = await save(value, version);
                  // A time shows as HH:MM, without the seconds the server keeps.
                  return isDate ? saved : { ...saved, value: shownTime(saved.value as string) };
                }}
              />
            </Labelled>
          </Fragment>
        );
      }
      case "ea_top_position":
        return text(key, key);
      case "embargoed":
        return toggle(key, key, release.embargoed);
      case "ea_top_page":
        return toggle(key, key, release.ea_top_page);
      case "authors":
        return (
          <div key={key} className="drawer-field">
            <label className="field-label" htmlFor="drawer-authors">
              {labelOf(key)}
            </label>
            <TextField
              id="drawer-authors"
              label={labelOf(key)}
              className="input"
              multiline
              value={release.authors.map(authorName).join("\n")}
              version={versions.authors}
              disabled={!canEdit}
              hint={t("data.authors_hint")}
              save={async (value, version) => {
                const lines = value
                  .split("\n")
                  .map((line) => line.trim())
                  .filter(Boolean);
                // A line left as it was keeps its given name, family name and ORCID.
                const authors = lines.map(
                  (line) => release.authors.find((author) => authorName(author) === line) ?? line,
                );
                const saved = await saver("authors")(authors, version);
                return {
                  value: (saved.value as Author[]).map(authorName).join("\n"),
                  version: saved.version,
                };
              }}
            />
          </div>
        );
      case "notes":
        return text(key, key, { multiline: true });
      default:
        return null;
    }
  }

  const readings = release.readings.flatMap((reading) => {
    const measure = context.measures.find((row) => row.id === reading.measure_id);
    return measure ? [{ reading, measure }] : [];
  });
  const custom = context.customFields.filter((field) => field.is_active);
  const missing = release.missing_required.map((key) => {
    if (!key.startsWith("custom_values.")) return labelOf(key);
    const field = context.customFields.find((row) => `custom_values.${row.key}` === key);
    return field ? (isJa && field.label_ja) || field.label_en : key;
  });
  const title = release.title ?? t("data.no_title");

  return (
    <SidePanel
      title={release.code ? `${release.code} · ${title}` : title}
      onClose={onClose}
      closeLabel={t("data.close")}
    >
      {missing.length > 0 && (
        <p className="notice-info mb-3xs">{t("data.still_needed", { fields: missing.join(", ") })}</p>
      )}
      <Section title={t("data.drawer_release")}>
        {configs.filter((c) => RELEASE_SECTION.has(c.key)).map((c) => coreControl(c.key))}
      </Section>
      <Section title={t("data.drawer_paper")}>
        {configs.filter((c) => PAPER_SECTION.has(c.key)).map((c) => coreControl(c.key))}
      </Section>
      <Section title={t("data.drawer_numbers")}>
        {readings.map(({ reading, measure }) => (
          <ReadingRow
            key={reading.id}
            release={release}
            reading={reading}
            measure={measure}
            context={context}
          />
        ))}
      </Section>
      {custom.length > 0 && (
        <Section title={t("data.drawer_custom")}>
          {custom.map((field) => (
            <CustomFieldRow key={field.id} release={release} field={field} context={context} />
          ))}
        </Section>
      )}
      {configs.some((c) => c.key === "notes") && (
        <Section title={labelOf("notes")}>{text("notes", "notes", { multiline: true })}</Section>
      )}
      <ResearcherFeedback releaseId={release.id} />
      <History release={release} context={context} />
      {canEdit && (
        <div className="drawer-section">
          <button type="button" className="btn-small" onClick={() => void remove()}>
            {t("data.remove")}
          </button>
          {removeError !== null && (
            <p role="alert" className="field-error">
              {errorMessage(t, removeError)}
            </p>
          )}
        </div>
      )}
    </SidePanel>
  );
}

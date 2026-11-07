import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { TFunction } from "i18next";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { http } from "../../api/client";
import { errorMessage } from "../../api/errors";
import type { Checkpoint, Measure } from "../../api/types";
import { SelectField, TextField, ToggleField } from "../../components/fields/Autosave";
import { useFieldSaver } from "../../components/fields/useFieldSaver";
import { translate } from "../../i18n";
import { SectionHeader, SubHeading } from "./SettingsLayout";

const CHECKPOINTS_KEY = ["checkpoints"];
const MEASURES_KEY = ["measures"];
// Metrics that exist at more than one moment, so they can be read at a new checkpoint.
const EXTENDABLE_METRICS = ["ea_views", "altmetric", "hp_views"];

function reminderOptions(t: TFunction) {
  return [
    { value: "0", label: t("settings.checkpoints.remind_on_day") },
    { value: "1", label: t("settings.checkpoints.remind_day_before") },
  ];
}

function CheckpointRow({ checkpoint }: { checkpoint: Checkpoint }) {
  const { t } = useTranslation();
  const saver = useFieldSaver(`/checkpoints/${checkpoint.id}`, CHECKPOINTS_KEY);
  const versions = checkpoint.field_versions;
  return (
    <tr>
      <td>
        <TextField
          label={t("settings.checkpoints.label_en")}
          value={checkpoint.label_en}
          version={versions.label_en}
          save={saver("label_en")}
        />
      </td>
      <td>
        <TextField
          label={t("settings.checkpoints.label_ja")}
          value={checkpoint.label_ja}
          version={versions.label_ja}
          save={saver("label_ja")}
        />
      </td>
      <td className="w-32">
        <TextField
          type="number"
          label={t("settings.checkpoints.offset")}
          value={checkpoint.offset_days}
          version={versions.offset_days}
          save={saver("offset_days")}
        />
      </td>
      <td className="w-44">
        <SelectField
          label={t("settings.checkpoints.remind")}
          value={String(checkpoint.remind_days_before)}
          version={versions.remind_days_before}
          save={saver("remind_days_before")}
          options={reminderOptions(t)}
        />
      </td>
    </tr>
  );
}

function NewCheckpoint() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [labelEn, setLabelEn] = useState("");
  const [labelJa, setLabelJa] = useState("");
  const [offset, setOffset] = useState("");
  const [remind, setRemind] = useState("0");
  const [error, setError] = useState<unknown>(null);

  async function submit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError(null);
    try {
      await http.post("/checkpoints", {
        values: {
          label_en: labelEn,
          label_ja: labelJa,
          offset_days: offset,
          remind_days_before: remind,
        },
      });
      setLabelEn("");
      setLabelJa("");
      setOffset("");
      setRemind("0");
      await queryClient.invalidateQueries({ queryKey: CHECKPOINTS_KEY });
    } catch (failure) {
      setError(failure);
    }
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="mt-3xs max-w-3xl">
      <div className="flex flex-wrap items-end gap-4xs">
        <input
          className="input max-w-52"
          aria-label={t("settings.checkpoints.label_en")}
          placeholder={t("settings.checkpoints.label_en")}
          required
          value={labelEn}
          onChange={(event) => setLabelEn(event.target.value)}
        />
        <input
          className="input max-w-52"
          aria-label={t("settings.checkpoints.label_ja")}
          placeholder={t("settings.checkpoints.label_ja")}
          value={labelJa}
          onChange={(event) => setLabelJa(event.target.value)}
        />
        <input
          className="input max-w-44"
          type="number"
          required
          aria-label={t("settings.checkpoints.offset")}
          placeholder={t("settings.checkpoints.offset")}
          value={offset}
          onChange={(event) => setOffset(event.target.value)}
        />
        <select
          className="input max-w-44"
          aria-label={t("settings.checkpoints.remind")}
          value={remind}
          onChange={(event) => setRemind(event.target.value)}
        >
          {reminderOptions(t).map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <button type="submit" className="btn-quiet">
          {t("settings.checkpoints.add")}
        </button>
      </div>
      {error !== null && (
        <p role="alert" className="field-error">
          {errorMessage(t, error)}
        </p>
      )}
    </form>
  );
}

function MeasureRow({ measure }: { measure: Measure }) {
  const { t } = useTranslation();
  const saver = useFieldSaver(`/measures/${measure.id}`, MEASURES_KEY);
  const versions = measure.field_versions;
  const locked = measure.source === "derived";
  return (
    <tr className={measure.is_active ? undefined : "opacity-60"}>
      <td>
        <TextField
          label={t("settings.checkpoints.label_en")}
          value={measure.label_en}
          version={versions.label_en}
          save={saver("label_en")}
        />
      </td>
      <td>
        <TextField
          label={t("settings.checkpoints.label_ja")}
          value={measure.label_ja}
          version={versions.label_ja}
          save={saver("label_ja")}
        />
      </td>
      <td>{translate(t, `settings.checkpoints.sources.${measure.source}`)}</td>
      <td>{translate(t, `settings.checkpoints.rules.${measure.applicability}`)}</td>
      <td className="w-40">
        <TextField
          type="date"
          label={t("settings.checkpoints.collected_from")}
          value={measure.collected_from}
          version={versions.collected_from}
          save={saver("collected_from")}
          disabled={locked}
        />
      </td>
      <td className="text-center">
        <ToggleField
          label={t("common.active")}
          title={locked ? t("settings.checkpoints.locked") : undefined}
          value={measure.is_active}
          version={versions.is_active}
          save={saver("is_active")}
          disabled={locked}
        />
      </td>
    </tr>
  );
}

function NewMeasure({ checkpoints }: { checkpoints: Checkpoint[] }) {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const [metric, setMetric] = useState(EXTENDABLE_METRICS[0]);
  const [checkpointId, setCheckpointId] = useState("");
  const [labelEn, setLabelEn] = useState("");
  const [labelJa, setLabelJa] = useState("");
  const [error, setError] = useState<unknown>(null);

  async function submit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError(null);
    try {
      await http.post("/measures", {
        metric,
        checkpoint_id: checkpointId,
        label_en: labelEn,
        label_ja: labelJa || null,
      });
      setLabelEn("");
      setLabelJa("");
      await queryClient.invalidateQueries({ queryKey: MEASURES_KEY });
    } catch (failure) {
      setError(failure);
    }
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="mt-3xs max-w-3xl">
      <div className="flex flex-wrap items-end gap-4xs">
        <select
          className="input max-w-52"
          aria-label={t("settings.checkpoints.metric")}
          value={metric}
          onChange={(event) => setMetric(event.target.value)}
        >
          {EXTENDABLE_METRICS.map((item) => (
            <option key={item} value={item}>
              {translate(t, `settings.checkpoints.metrics.${item}`)}
            </option>
          ))}
        </select>
        <select
          className="input max-w-52"
          aria-label={t("settings.checkpoints.at_checkpoint")}
          required
          value={checkpointId}
          onChange={(event) => setCheckpointId(event.target.value)}
        >
          <option value="">{t("settings.checkpoints.at_checkpoint")}</option>
          {checkpoints.map((checkpoint) => (
            <option key={checkpoint.id} value={checkpoint.id}>
              {(i18n.language === "ja" && checkpoint.label_ja) || checkpoint.label_en}
            </option>
          ))}
        </select>
        <input
          className="input max-w-52"
          aria-label={t("settings.checkpoints.label_en")}
          placeholder={t("settings.checkpoints.label_en")}
          required
          value={labelEn}
          onChange={(event) => setLabelEn(event.target.value)}
        />
        <input
          className="input max-w-52"
          aria-label={t("settings.checkpoints.label_ja")}
          placeholder={t("settings.checkpoints.label_ja")}
          value={labelJa}
          onChange={(event) => setLabelJa(event.target.value)}
        />
        <button type="submit" className="btn-quiet">
          {t("settings.checkpoints.add_measure")}
        </button>
      </div>
      {error !== null && (
        <p role="alert" className="field-error">
          {errorMessage(t, error)}
        </p>
      )}
    </form>
  );
}

export default function CheckpointsSettings() {
  const { t } = useTranslation();
  const { data: checkpoints } = useQuery({
    queryKey: CHECKPOINTS_KEY,
    queryFn: () => http.get<Checkpoint[]>("/checkpoints"),
  });
  const { data: measures } = useQuery({
    queryKey: MEASURES_KEY,
    queryFn: () => http.get<Measure[]>("/measures"),
  });

  return (
    <div>
      <SectionHeader
        title={t("settings.sections.checkpoints")}
        help={t("settings.help.checkpoints")}
      />
      <SubHeading>{t("settings.checkpoints.checkpoints_title")}</SubHeading>
      <p className="mb-4xs max-w-3xl text-content-secondary">
        {t("settings.checkpoints.offset_help")}
      </p>
      <div className="table-scroll max-w-4xl">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("settings.checkpoints.label_en")}</th>
              <th>{t("settings.checkpoints.label_ja")}</th>
              <th>{t("settings.checkpoints.offset")}</th>
              <th>{t("settings.checkpoints.remind")}</th>
            </tr>
          </thead>
          <tbody>
            {(checkpoints ?? []).map((checkpoint) => (
              <CheckpointRow key={checkpoint.id} checkpoint={checkpoint} />
            ))}
          </tbody>
        </table>
      </div>
      <NewCheckpoint />

      <SubHeading>{t("settings.checkpoints.measures_title")}</SubHeading>
      <p className="mb-4xs max-w-3xl text-content-secondary">
        {t("settings.checkpoints.measures_help")}
      </p>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("settings.checkpoints.label_en")}</th>
              <th>{t("settings.checkpoints.label_ja")}</th>
              <th>{t("settings.checkpoints.source")}</th>
              <th>{t("settings.checkpoints.applies")}</th>
              <th>{t("settings.checkpoints.collected_from")}</th>
              <th>{t("common.active")}</th>
            </tr>
          </thead>
          <tbody>
            {(measures ?? []).map((measure) => (
              <MeasureRow key={measure.id} measure={measure} />
            ))}
          </tbody>
        </table>
      </div>
      <NewMeasure checkpoints={checkpoints ?? []} />

      <SubHeading>{t("settings.checkpoints.reminders_title")}</SubHeading>
      <p className="max-w-3xl text-content-secondary">{t("settings.checkpoints.reminders_later")}</p>
    </div>
  );
}

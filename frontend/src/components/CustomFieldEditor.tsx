import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { http } from "../api/client";
import { errorMessage } from "../api/errors";
import type {
  Checkpoint,
  CustomField,
  CustomFieldOption,
  CustomFieldType,
  Vocabulary,
} from "../api/types";
import ConfirmButton from "./ConfirmButton";
import { SelectField, TextField, ToggleField } from "./fields/Autosave";
import { useFieldSaver } from "./fields/useFieldSaver";

const FIELD_TYPES: CustomFieldType[] = [
  "integer",
  "number",
  "text",
  "long_text",
  "date",
  "boolean",
  "single_select",
  "multi_select",
  "url",
];
const NUMERIC: CustomFieldType[] = ["integer", "number"];
const SELECTS: CustomFieldType[] = ["single_select", "multi_select"];
const QUERY_KEY = ["custom-fields"];

/** "English | 日本語", one per line, as the options editor shows them. */
export function parseOptions(
  text: string,
): { label_en: string; label_ja: string | null }[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [english, japanese] = line.split("|").map((part) => part.trim());
      return { label_en: english, label_ja: japanese || null };
    });
}

export function formatOptions(options: CustomFieldOption[]): string {
  return options
    .map((option) =>
      option.label_ja
        ? `${option.label_en} | ${option.label_ja}`
        : option.label_en,
    )
    .join("\n");
}

function useCheckpointOptions() {
  const { i18n } = useTranslation();
  const { data } = useQuery({
    queryKey: ["checkpoints"],
    queryFn: () => http.get<Checkpoint[]>("/checkpoints"),
  });
  return (data ?? []).map((checkpoint) => ({
    value: checkpoint.id,
    label:
      (i18n.language === "ja" && checkpoint.label_ja) || checkpoint.label_en,
  }));
}

function FieldRow({
  field,
  canMoveUp,
  canMoveDown,
  onMove,
}: {
  field: CustomField;
  canMoveUp: boolean;
  canMoveDown: boolean;
  onMove: (direction: -1 | 1) => void;
}) {
  const { t, i18n } = useTranslation();
  const saver = useFieldSaver(`/custom-fields/${field.id}`, QUERY_KEY);
  const queryClient = useQueryClient();
  const checkpoints = useCheckpointOptions();
  const { data: vocabularies } = useQuery({
    queryKey: ["lists", "vocabularies"],
    queryFn: () => http.get<Vocabulary[]>("/lists/vocabularies"),
  });
  const versions = field.field_versions;
  const isInstitution = field.scope === "institution";
  const isSelect = SELECTS.includes(field.field_type);

  return (
    <tr>
      <td>
        <TextField
          label={t("custom_field.label_en")}
          value={field.label_en}
          version={versions.label_en}
          save={saver("label_en")}
        />
        <p className="px-5xs text-sm text-content-secondary">{field.key}</p>
        {field.import_heading && (
          <p className="px-5xs text-sm text-content-secondary">
            {t("custom_field.from_column", { column: field.import_heading })}
          </p>
        )}
      </td>
      <td>
        <TextField
          label={t("custom_field.label_ja")}
          value={field.label_ja}
          version={versions.label_ja}
          save={saver("label_ja")}
        />
      </td>
      <td className="whitespace-nowrap">
        {t(`custom_field.types.${field.field_type}`)}
      </td>
      <td>
        {isSelect && (
          <>
            <SelectField
              label={t("custom_field.vocabulary")}
              value={field.vocabulary_id}
              version={versions.vocabulary_id}
              save={saver("vocabulary_id")}
              emptyLabel={t("custom_field.options_on_field")}
              options={(vocabularies ?? []).map((vocabulary) => ({
                value: vocabulary.id,
                label:
                  (i18n.language === "ja" && vocabulary.name_ja) ||
                  vocabulary.name_en,
              }))}
            />
            {!field.vocabulary_id && (
              <p className="px-5xs text-sm text-content-secondary">
                {field.options.map((option) => option.label_en).join(", ")}
              </p>
            )}
          </>
        )}
      </td>
      <td>
        <SelectField
          label={t("custom_field.due")}
          value={field.due_checkpoint_id}
          version={versions.due_checkpoint_id}
          save={saver("due_checkpoint_id")}
          emptyLabel={t("common.none")}
          options={checkpoints}
        />
      </td>
      {isInstitution && (
        <>
          <td className="text-center">
            <ToggleField
              label={t("custom_field.required")}
              value={field.required}
              version={versions.required}
              save={saver("required")}
            />
          </td>
          <td className="text-center">
            <ToggleField
              label={t("custom_field.score_eligible")}
              value={field.score_eligible}
              version={versions.score_eligible}
              save={saver("score_eligible")}
              disabled={!NUMERIC.includes(field.field_type)}
            />
          </td>
        </>
      )}
      <td className="text-center">
        <ToggleField
          label={t("common.active")}
          value={field.is_active}
          version={versions.is_active}
          save={saver("is_active")}
        />
      </td>
      {!isInstitution && (
        <td>
          {/* The owner can hand their field to everyone (Daniel, 2026-11-12). */}
          <ConfirmButton
            label={t("custom_field.share")}
            question={t("custom_field.share_question")}
            onConfirm={() =>
              void http
                .post(`/custom-fields/${field.id}/convert`)
                .then(() =>
                  queryClient.invalidateQueries({ queryKey: QUERY_KEY }),
                )
            }
          />
        </td>
      )}
      <td className="whitespace-nowrap">
        <button
          type="button"
          className="btn-small"
          disabled={!canMoveUp}
          aria-label={t("common.move_up")}
          onClick={() => onMove(-1)}
        >
          ↑
        </button>{" "}
        <button
          type="button"
          className="btn-small"
          disabled={!canMoveDown}
          aria-label={t("common.move_down")}
          onClick={() => onMove(1)}
        >
          ↓
        </button>
      </td>
    </tr>
  );
}

function NewFieldForm({ scope }: { scope: "institution" | "personal" }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const checkpoints = useCheckpointOptions();
  const [labelEn, setLabelEn] = useState("");
  const [labelJa, setLabelJa] = useState("");
  const [fieldType, setFieldType] = useState<CustomFieldType>("integer");
  const [options, setOptions] = useState("");
  const [due, setDue] = useState("");
  const [error, setError] = useState<unknown>(null);
  const isSelect = SELECTS.includes(fieldType);

  async function submit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError(null);
    try {
      await http.post("/custom-fields", {
        scope,
        label_en: labelEn,
        label_ja: labelJa || null,
        field_type: fieldType,
        options: isSelect ? parseOptions(options) : [],
        due_checkpoint_id: due || null,
      });
      setLabelEn("");
      setLabelJa("");
      setOptions("");
      setDue("");
      await queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    } catch (failure) {
      setError(failure);
    }
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="mt-2xs max-w-3xl">
      <div className="grid gap-4xs sm:grid-cols-2">
        <div>
          <label className="field-label" htmlFor={`${scope}-label-en`}>
            {t("custom_field.label_en")}
          </label>
          <input
            id={`${scope}-label-en`}
            className="input"
            required
            value={labelEn}
            onChange={(event) => setLabelEn(event.target.value)}
          />
        </div>
        <div>
          <label className="field-label" htmlFor={`${scope}-label-ja`}>
            {t("custom_field.label_ja")}
          </label>
          <input
            id={`${scope}-label-ja`}
            className="input"
            value={labelJa}
            onChange={(event) => setLabelJa(event.target.value)}
          />
        </div>
        <div>
          <label className="field-label" htmlFor={`${scope}-type`}>
            {t("custom_field.type")}
          </label>
          <select
            id={`${scope}-type`}
            className="input"
            value={fieldType}
            onChange={(event) =>
              setFieldType(event.target.value as CustomFieldType)
            }
          >
            {FIELD_TYPES.map((type) => (
              <option key={type} value={type}>
                {t(`custom_field.types.${type}`)}
              </option>
            ))}
          </select>
          <p className="field-hint">{t("custom_field.type_hint")}</p>
        </div>
        <div>
          <label className="field-label" htmlFor={`${scope}-due`}>
            {t("custom_field.due")}
          </label>
          <select
            id={`${scope}-due`}
            className="input"
            value={due}
            onChange={(event) => setDue(event.target.value)}
          >
            <option value="">{t("common.none")}</option>
            {checkpoints.map((checkpoint) => (
              <option key={checkpoint.value} value={checkpoint.value}>
                {checkpoint.label}
              </option>
            ))}
          </select>
          <p className="field-hint">{t("custom_field.due_hint")}</p>
        </div>
        {isSelect && (
          <div className="sm:col-span-2">
            <label className="field-label" htmlFor={`${scope}-options`}>
              {t("custom_field.options")}
            </label>
            <textarea
              id={`${scope}-options`}
              className="input"
              rows={3}
              value={options}
              onChange={(event) => setOptions(event.target.value)}
            />
            <p className="field-hint">{t("custom_field.options_hint")}</p>
          </div>
        )}
      </div>
      {error !== null && (
        <p role="alert" className="field-error">
          {errorMessage(t, error)}
        </p>
      )}
      <button type="submit" className="btn-primary mt-4xs">
        {t("custom_field.add")}
      </button>
    </form>
  );
}

/** Institution fields in Settings, and a person's own fields under My fields. */
export default function CustomFieldEditor({
  scope,
  ownerId,
}: {
  scope: "institution" | "personal";
  ownerId?: string;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => http.get<CustomField[]>("/custom-fields"),
    refetchInterval: 60_000,
  });
  const fields = (data ?? []).filter(
    (field) =>
      field.scope === scope &&
      (scope === "institution" || field.owner_id === ownerId),
  );
  const isInstitution = scope === "institution";

  async function move(index: number, direction: -1 | 1): Promise<void> {
    const ids = fields.map((field) => field.id);
    [ids[index], ids[index + direction]] = [ids[index + direction], ids[index]];
    await http.post("/custom-fields/reorder", { ids });
    await queryClient.invalidateQueries({ queryKey: QUERY_KEY });
  }

  return (
    <div>
      {fields.length === 0 ? (
        <p className="text-content-secondary">{t("custom_field.none_yet")}</p>
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t("custom_field.label_en")}</th>
                <th>{t("custom_field.label_ja")}</th>
                <th>{t("custom_field.type")}</th>
                <th>{t("custom_field.options")}</th>
                <th>{t("custom_field.due")}</th>
                {isInstitution && (
                  <>
                    <th>{t("custom_field.required")}</th>
                    <th>{t("custom_field.score_eligible")}</th>
                  </>
                )}
                <th>{t("common.active")}</th>
                {!isInstitution && <th>{t("custom_field.share_heading")}</th>}
                <th>{t("common.order")}</th>
              </tr>
            </thead>
            <tbody>
              {fields.map((field, index) => (
                <FieldRow
                  key={field.id}
                  field={field}
                  canMoveUp={index > 0}
                  canMoveDown={index < fields.length - 1}
                  onMove={(direction) => void move(index, direction)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
      <NewFieldForm scope={scope} />
    </div>
  );
}

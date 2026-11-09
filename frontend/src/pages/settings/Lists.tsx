import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, useParams } from "react-router-dom";

import { http } from "../../api/client";
import type {
  Institution,
  ReleaseType,
  ResearchField,
  Unit,
  User,
  Vocabulary,
  VocabularyItem,
  Writer,
} from "../../api/types";
import AddEntry from "../../components/AddEntry";
import CsvTools from "../../components/CsvTools";
import { SelectField, TextField, ToggleField } from "../../components/fields/Autosave";
import { useFieldSaver } from "../../components/fields/useFieldSaver";
import { SectionHeader, SubHeading } from "./SettingsLayout";

const KINDS = ["units", "fields", "writers", "release_types", "vocabularies"] as const;
const INSTITUTION_KEY = ["settings", "institution"];
const UNIT_TYPES = ["school", "institute", "center", "other"] as const;

function useList<T>(kind: string) {
  return useQuery({
    queryKey: ["lists", kind],
    queryFn: () => http.get<T[]>(`/lists/${kind}`),
    refetchInterval: 60_000,
  });
}

function useAdd(path: string, invalidate: string[]) {
  const queryClient = useQueryClient();
  return async (values: Record<string, unknown>) => {
    await http.post(path, { values });
    await queryClient.invalidateQueries({ queryKey: invalidate });
  };
}

function useRefresh(invalidate: string[]) {
  const queryClient = useQueryClient();
  return () => void queryClient.invalidateQueries({ queryKey: invalidate });
}

function UnitRow({ unit, fields }: { unit: Unit; fields: ResearchField[] }) {
  const { t, i18n } = useTranslation();
  const saver = useFieldSaver(`/lists/units/${unit.id}`, ["lists", "units"]);
  const versions = unit.field_versions;
  return (
    <tr className={unit.is_active ? undefined : "opacity-60"}>
      <td>
        <TextField
          label={t("settings.lists.name_en")}
          value={unit.name_en}
          version={versions.name_en}
          save={saver("name_en")}
        />
      </td>
      <td>
        <TextField
          label={t("settings.lists.name_ja")}
          value={unit.name_ja}
          version={versions.name_ja}
          save={saver("name_ja")}
        />
      </td>
      <td>
        <TextField
          label={t("settings.lists.short_label")}
          value={unit.short_label}
          version={versions.short_label}
          save={saver("short_label")}
        />
      </td>
      <td>
        <SelectField
          label={t("settings.lists.type")}
          value={unit.unit_type}
          version={versions.unit_type}
          save={saver("unit_type")}
          emptyLabel={t("common.none")}
          options={UNIT_TYPES.map((type) => ({
            value: type,
            label: t(`settings.lists.types.${type}`),
          }))}
        />
      </td>
      <td>
        <TextField
          label={t("settings.lists.aliases")}
          value={unit.aliases.join(", ")}
          version={versions.aliases}
          save={async (value, version) => {
            const result = await saver("aliases")(value, version);
            return { ...result, value: (result.value as string[]).join(", ") };
          }}
        />
      </td>
      <td>
        <SelectField
          label={t("settings.lists.default_field")}
          value={unit.default_field_id}
          version={versions.default_field_id}
          save={saver("default_field_id")}
          emptyLabel={t("common.none")}
          options={fields.map((field) => ({
            value: field.id,
            label: (i18n.language === "ja" && field.name_ja) || field.name_en,
          }))}
        />
      </td>
      <td className="text-center">
        <ToggleField
          label={t("common.active")}
          value={unit.is_active}
          version={versions.is_active}
          save={saver("is_active")}
        />
      </td>
    </tr>
  );
}

function Units() {
  const { t } = useTranslation();
  const { data } = useList<Unit>("units");
  const { data: fields } = useList<ResearchField>("fields");
  const add = useAdd("/lists/units", ["lists", "units"]);
  const refresh = useRefresh(["lists", "units"]);
  return (
    <>
      <CsvTools
        exportPath="/lists/units/export"
        importPath="/lists/units/import"
        filename="units.csv"
        onImported={refresh}
      />
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("settings.lists.name_en")}</th>
              <th>{t("settings.lists.name_ja")}</th>
              <th>{t("settings.lists.short_label")}</th>
              <th>{t("settings.lists.type")}</th>
              <th>{t("settings.lists.aliases")}</th>
              <th>{t("settings.lists.default_field")}</th>
              <th>{t("common.active")}</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((unit) => (
              <UnitRow key={unit.id} unit={unit} fields={fields ?? []} />
            ))}
          </tbody>
        </table>
      </div>
      <AddEntry label={t("settings.lists.add_unit")} onAdd={(name) => add({ name_en: name })} />
    </>
  );
}

function FieldRow({ field }: { field: ResearchField }) {
  const { t } = useTranslation();
  const saver = useFieldSaver(`/lists/fields/${field.id}`, ["lists", "fields"]);
  const versions = field.field_versions;
  return (
    <tr className={field.is_active ? undefined : "opacity-60"}>
      <td>
        <TextField
          label={t("settings.lists.name_en")}
          value={field.name_en}
          version={versions.name_en}
          save={saver("name_en")}
        />
      </td>
      <td>
        <TextField
          label={t("settings.lists.name_ja")}
          value={field.name_ja}
          version={versions.name_ja}
          save={saver("name_ja")}
        />
      </td>
      <td className="w-1/2">
        <TextField
          multiline
          label={t("settings.lists.scope_note")}
          value={field.scope_note}
          version={versions.scope_note}
          save={saver("scope_note")}
        />
      </td>
      <td className="text-center">
        <ToggleField
          label={t("common.active")}
          value={field.is_active}
          version={versions.is_active}
          save={saver("is_active")}
        />
      </td>
    </tr>
  );
}

function Fields() {
  const { t } = useTranslation();
  const { data } = useList<ResearchField>("fields");
  const add = useAdd("/lists/fields", ["lists", "fields"]);
  const refresh = useRefresh(["lists", "fields"]);
  return (
    <>
      <CsvTools
        exportPath="/lists/fields/export"
        importPath="/lists/fields/import"
        filename="fields.csv"
        onImported={refresh}
      />
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("settings.lists.name_en")}</th>
              <th>{t("settings.lists.name_ja")}</th>
              <th>{t("settings.lists.scope_note")}</th>
              <th>{t("common.active")}</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((field) => (
              <FieldRow key={field.id} field={field} />
            ))}
          </tbody>
        </table>
      </div>
      <AddEntry label={t("settings.lists.add_field")} onAdd={(name) => add({ name_en: name })} />
    </>
  );
}

function WriterRow({ writer, users }: { writer: Writer; users: User[] }) {
  const { t } = useTranslation();
  const saver = useFieldSaver(`/lists/writers/${writer.id}`, ["lists", "writers"]);
  const versions = writer.field_versions;
  return (
    <tr className={writer.is_active ? undefined : "opacity-60"}>
      <td>
        <TextField
          label={t("settings.lists.display_name_en")}
          value={writer.display_name_en}
          version={versions.display_name_en}
          save={saver("display_name_en")}
        />
      </td>
      <td>
        <TextField
          label={t("settings.lists.display_name_ja")}
          value={writer.display_name_ja}
          version={versions.display_name_ja}
          save={saver("display_name_ja")}
        />
      </td>
      <td>
        <TextField
          label={t("settings.lists.full_name")}
          value={writer.full_name}
          version={versions.full_name}
          save={saver("full_name")}
        />
      </td>
      <td>
        <SelectField
          label={t("settings.lists.linked_user")}
          value={writer.user_id}
          version={versions.user_id}
          save={saver("user_id")}
          emptyLabel={t("settings.lists.no_account")}
          options={users.map((user) => ({
            value: user.id,
            label: user.full_name ?? user.email,
          }))}
        />
      </td>
      <td className="text-center">
        <ToggleField
          label={t("common.active")}
          value={writer.is_active}
          version={versions.is_active}
          save={saver("is_active")}
        />
      </td>
    </tr>
  );
}

function Writers() {
  const { t } = useTranslation();
  const { data } = useList<Writer>("writers");
  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => http.get<User[]>("/users"),
  });
  const add = useAdd("/lists/writers", ["lists", "writers"]);
  const refresh = useRefresh(["lists", "writers"]);
  return (
    <>
      <p className="mb-3xs max-w-3xl text-content-secondary">{t("settings.lists.writers_help")}</p>
      <CsvTools
        exportPath="/lists/writers/export"
        importPath="/lists/writers/import"
        filename="writers.csv"
        personalData
        onImported={refresh}
      />
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("settings.lists.display_name_en")}</th>
              <th>{t("settings.lists.display_name_ja")}</th>
              <th>{t("settings.lists.full_name")}</th>
              <th>{t("settings.lists.linked_user")}</th>
              <th>{t("common.active")}</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((writer) => (
              <WriterRow key={writer.id} writer={writer} users={users ?? []} />
            ))}
          </tbody>
        </table>
      </div>
      <AddEntry
        label={t("settings.lists.add_writer")}
        onAdd={(name) => add({ display_name_en: name })}
      />
    </>
  );
}

function ReleaseTypeRow({ kind }: { kind: ReleaseType }) {
  const { t } = useTranslation();
  const saver = useFieldSaver(`/lists/release_types/${kind.id}`, ["lists", "release_types"]);
  const versions = kind.field_versions;
  return (
    <tr className={kind.is_active ? undefined : "opacity-60"}>
      <td className="w-20">
        <TextField
          type="number"
          label={t("settings.lists.position")}
          value={kind.position}
          version={versions.position}
          save={saver("position")}
        />
      </td>
      <td>
        <TextField
          label={t("settings.lists.name_en")}
          value={kind.name_en}
          version={versions.name_en}
          save={saver("name_en")}
        />
      </td>
      <td>
        <TextField
          label={t("settings.lists.name_ja")}
          value={kind.name_ja}
          version={versions.name_ja}
          save={saver("name_ja")}
        />
      </td>
      <td>
        <TextField
          label={t("settings.lists.aliases")}
          value={kind.aliases.join(", ")}
          version={versions.aliases}
          save={async (value, version) => {
            const result = await saver("aliases")(value, version);
            return { ...result, value: (result.value as string[]).join(", ") };
          }}
        />
      </td>
      <td className="text-center">
        <ToggleField
          label={t("common.active")}
          value={kind.is_active}
          version={versions.is_active}
          save={saver("is_active")}
        />
      </td>
    </tr>
  );
}

/** R6.4.1: EurekAlert's categories, and which one a new release starts as. */
function ReleaseTypes() {
  const { t, i18n } = useTranslation();
  const { data } = useList<ReleaseType>("release_types");
  const { data: institution } = useQuery({
    queryKey: INSTITUTION_KEY,
    queryFn: () => http.get<Institution>("/settings/institution"),
  });
  const saveInstitution = useFieldSaver("/settings/institution", INSTITUTION_KEY);
  const add = useAdd("/lists/release_types", ["lists", "release_types"]);
  const refresh = useRefresh(["lists", "release_types"]);
  const rows = data ?? [];
  const chosen = institution?.default_release_type_id ?? null;
  return (
    <>
      <p className="mb-3xs max-w-3xl text-content-secondary">
        {t("settings.lists.release_types_help")}
      </p>
      {institution && (
        <div className="mb-2xs max-w-md">
          <label className="field-label" htmlFor="default-release-type">
            {t("settings.lists.default_release_type")}
          </label>
          <SelectField
            id="default-release-type"
            className="input"
            label={t("settings.lists.default_release_type")}
            value={chosen}
            version={institution.field_versions.default_release_type_id}
            save={saveInstitution("default_release_type_id")}
            emptyLabel={t("settings.lists.no_default_release_type")}
            hint={t("settings.lists.default_release_type_hint")}
            options={rows
              .filter((row) => row.is_active || row.id === chosen)
              .map((row) => ({
                value: row.id,
                label: (i18n.language === "ja" && row.name_ja) || row.name_en,
              }))}
          />
        </div>
      )}
      <CsvTools
        exportPath="/lists/release_types/export"
        importPath="/lists/release_types/import"
        filename="release_types.csv"
        onImported={refresh}
      />
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("settings.lists.position")}</th>
              <th>{t("settings.lists.name_en")}</th>
              <th>{t("settings.lists.name_ja")}</th>
              <th>{t("settings.lists.aliases")}</th>
              <th>{t("common.active")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((kind) => (
              <ReleaseTypeRow key={kind.id} kind={kind} />
            ))}
          </tbody>
        </table>
      </div>
      <AddEntry
        label={t("settings.lists.add_release_type")}
        onAdd={(name) => add({ name_en: name })}
      />
    </>
  );
}

function ItemRow({ item, vocabularyId }: { item: VocabularyItem; vocabularyId: string }) {
  const { t } = useTranslation();
  const saver = useFieldSaver(`/lists/vocabulary-items/${item.id}`, [
    "lists",
    "vocabularies",
    vocabularyId,
  ]);
  const versions = item.field_versions;
  return (
    <tr className={item.is_active ? undefined : "opacity-60"}>
      <td>
        <TextField
          label={t("settings.lists.name_en")}
          value={item.label_en}
          version={versions.label_en}
          save={saver("label_en")}
        />
      </td>
      <td>
        <TextField
          label={t("settings.lists.name_ja")}
          value={item.label_ja}
          version={versions.label_ja}
          save={saver("label_ja")}
        />
      </td>
      <td>
        <TextField
          label={t("settings.lists.aliases")}
          value={item.aliases.join(", ")}
          version={versions.aliases}
          save={async (value, version) => {
            const result = await saver("aliases")(value, version);
            return { ...result, value: (result.value as string[]).join(", ") };
          }}
        />
      </td>
      <td className="text-center">
        <ToggleField
          label={t("common.active")}
          value={item.is_active}
          version={versions.is_active}
          save={saver("is_active")}
        />
      </td>
    </tr>
  );
}

function VocabularyItems({ vocabulary }: { vocabulary: Vocabulary }) {
  const { t, i18n } = useTranslation();
  const path = `/lists/vocabularies/${vocabulary.id}/items`;
  const queryKey = ["lists", "vocabularies", vocabulary.id];
  const { data } = useQuery({ queryKey, queryFn: () => http.get<VocabularyItem[]>(path) });
  const add = useAdd(path, queryKey);
  const refresh = useRefresh(queryKey);
  const name = (i18n.language === "ja" && vocabulary.name_ja) || vocabulary.name_en;
  return (
    <>
      <SubHeading>{t("settings.lists.items_of", { name })}</SubHeading>
      <CsvTools
        exportPath={`${path}/export`}
        importPath={`${path}/import`}
        filename={`vocabulary_${vocabulary.key}.csv`}
        onImported={refresh}
      />
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("settings.lists.name_en")}</th>
              <th>{t("settings.lists.name_ja")}</th>
              <th>{t("settings.lists.aliases")}</th>
              <th>{t("common.active")}</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((item) => (
              <ItemRow key={item.id} item={item} vocabularyId={vocabulary.id} />
            ))}
          </tbody>
        </table>
      </div>
      <AddEntry label={t("settings.lists.add_item")} onAdd={(label) => add({ label_en: label })} />
    </>
  );
}

function VocabularyRow({
  vocabulary,
  selected,
  onSelect,
}: {
  vocabulary: Vocabulary;
  selected: boolean;
  onSelect: () => void;
}) {
  const { t } = useTranslation();
  const saver = useFieldSaver(`/lists/vocabularies/${vocabulary.id}`, ["lists", "vocabularies"]);
  const versions = vocabulary.field_versions;
  return (
    <tr className={vocabulary.is_active ? undefined : "opacity-60"}>
      <td>
        <TextField
          label={t("settings.lists.name_en")}
          value={vocabulary.name_en}
          version={versions.name_en}
          save={saver("name_en")}
        />
      </td>
      <td>
        <TextField
          label={t("settings.lists.name_ja")}
          value={vocabulary.name_ja}
          version={versions.name_ja}
          save={saver("name_ja")}
        />
      </td>
      <td className="text-center">
        <ToggleField
          label={t("common.active")}
          value={vocabulary.is_active}
          version={versions.is_active}
          save={saver("is_active")}
        />
      </td>
      <td>
        <button type="button" className="btn-small" aria-pressed={selected} onClick={onSelect}>
          {t("settings.lists.show_items")}
        </button>
      </td>
    </tr>
  );
}

function Vocabularies() {
  const { t } = useTranslation();
  const { data } = useList<Vocabulary>("vocabularies");
  const add = useAdd("/lists/vocabularies", ["lists", "vocabularies"]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = data?.find((vocabulary) => vocabulary.id === selectedId);
  return (
    <>
      <p className="mb-3xs max-w-3xl text-content-secondary">
        {t("settings.lists.vocabularies_help")}
      </p>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("settings.lists.name_en")}</th>
              <th>{t("settings.lists.name_ja")}</th>
              <th>{t("common.active")}</th>
              <th>{t("common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((vocabulary) => (
              <VocabularyRow
                key={vocabulary.id}
                vocabulary={vocabulary}
                selected={vocabulary.id === selectedId}
                onSelect={() => setSelectedId(vocabulary.id)}
              />
            ))}
          </tbody>
        </table>
      </div>
      <AddEntry
        label={t("settings.lists.add_vocabulary")}
        onAdd={(name) => add({ name_en: name })}
      />
      {selected && <VocabularyItems key={selected.id} vocabulary={selected} />}
    </>
  );
}

export default function ListsSettings() {
  const { t } = useTranslation();
  const { kind = "units" } = useParams();
  return (
    <div>
      <SectionHeader title={t("settings.sections.lists")} help={t("settings.help.lists")} />
      <nav aria-label={t("settings.sections.lists")} className="mb-2xs flex flex-wrap gap-5xs">
        {KINDS.map((item) => (
          <NavLink
            key={item}
            to={`/settings/lists/${item}`}
            className={({ isActive }) =>
              isActive || (kind === item && item === "units")
                ? "nav-link nav-link-active"
                : "nav-link"
            }
          >
            {t(`settings.lists.kinds.${item}`)}
          </NavLink>
        ))}
      </nav>
      {kind === "units" && <Units />}
      {kind === "fields" && <Fields />}
      {kind === "writers" && <Writers />}
      {kind === "release_types" && <ReleaseTypes />}
      {kind === "vocabularies" && <Vocabularies />}
    </div>
  );
}

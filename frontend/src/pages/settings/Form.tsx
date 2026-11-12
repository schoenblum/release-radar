import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { http } from "../../api/client";
import type { CoreField } from "../../api/types";
import CustomFieldEditor from "../../components/CustomFieldEditor";
import { TextField, ToggleField } from "../../components/fields/Autosave";
import { useFieldSaver } from "../../components/fields/useFieldSaver";
import { translate } from "../../i18n";
import { SectionHeader, SubHeading } from "./SettingsLayout";

const QUERY_KEY = ["core-fields"];

function CoreFieldRow({
  field,
  canMoveUp,
  canMoveDown,
  onMove,
}: {
  field: CoreField;
  canMoveUp: boolean;
  canMoveDown: boolean;
  onMove: (direction: -1 | 1) => void;
}) {
  const { t } = useTranslation();
  const saver = useFieldSaver(`/core-fields/${field.id}`, QUERY_KEY);
  const versions = field.field_versions;
  const defaultLabel = translate(t, `release_fields.${field.key}`);
  return (
    <tr>
      <td className="whitespace-nowrap">{defaultLabel}</td>
      <td>
        <TextField
          label={t("settings.form.label_en")}
          value={field.label_en}
          version={versions.label_en}
          save={saver("label_en")}
        />
      </td>
      <td>
        <TextField
          label={t("settings.form.label_ja")}
          value={field.label_ja}
          version={versions.label_ja}
          save={saver("label_ja")}
        />
      </td>
      <td className="text-center">
        <ToggleField
          label={t("settings.form.in_grid_label", { name: defaultLabel })}
          title={field.can_leave_grid ? undefined : t("settings.form.always_in_grid")}
          value={field.in_grid}
          version={versions.in_grid}
          save={saver("in_grid")}
          disabled={!field.can_leave_grid}
        />
      </td>
      <td className="text-center">
        <ToggleField
          label={t("settings.form.in_record_label", { name: defaultLabel })}
          title={field.can_leave_record ? undefined : t("settings.form.always_in_record")}
          value={field.in_record}
          version={versions.in_record}
          save={saver("in_record")}
          disabled={!field.can_leave_record}
        />
      </td>
      <td className="text-center">
        <ToggleField
          label={t("settings.form.required")}
          title={field.can_require ? undefined : t("settings.form.cannot_require")}
          value={field.required}
          version={versions.required}
          save={saver("required")}
          disabled={!field.can_require}
        />
      </td>
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

export default function FormSettings() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => http.get<CoreField[]>("/core-fields"),
  });
  const fields = data ?? [];

  async function move(index: number, direction: -1 | 1): Promise<void> {
    const ids = fields.map((field) => field.id);
    [ids[index], ids[index + direction]] = [ids[index + direction], ids[index]];
    await http.post("/core-fields/reorder", { ids });
    await queryClient.invalidateQueries({ queryKey: QUERY_KEY });
  }

  return (
    <div>
      <SectionHeader title={t("settings.sections.form")} help={t("settings.help.form")} />
      <SubHeading>{t("settings.form.core_title")}</SubHeading>
      <p className="mb-4xs max-w-3xl text-content-secondary">{t("settings.form.core_help")}</p>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("settings.form.field")}</th>
              <th>{t("settings.form.label_en")}</th>
              <th>{t("settings.form.label_ja")}</th>
              <th>{t("settings.form.in_grid")}</th>
              <th>{t("settings.form.in_record")}</th>
              <th>{t("settings.form.required")}</th>
              <th>{t("common.order")}</th>
            </tr>
          </thead>
          <tbody>
            {fields.map((field, index) => (
              <CoreFieldRow
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

      <SubHeading>{t("settings.form.custom_title")}</SubHeading>
      <p className="mb-4xs max-w-3xl text-content-secondary">{t("settings.form.custom_help")}</p>
      <CustomFieldEditor scope="institution" />
    </div>
  );
}

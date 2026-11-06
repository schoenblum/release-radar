import { useTranslation } from "react-i18next";

import { useAuth } from "../auth";
import CustomFieldEditor from "../components/CustomFieldEditor";
import { SectionHeader } from "./settings/SettingsLayout";

/** Fields people track for themselves (R7.3.1). Reached from the user menu, not Settings. */
export default function MyFields() {
  const { t } = useTranslation();
  const { user } = useAuth();
  return (
    <div>
      <SectionHeader title={t("my_fields.title")} help={t("my_fields.help")} />
      <CustomFieldEditor scope="personal" ownerId={user?.id} />
    </div>
  );
}

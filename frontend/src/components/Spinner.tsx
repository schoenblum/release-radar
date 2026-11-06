import { useTranslation } from "react-i18next";

export function PageLoading() {
  const { t } = useTranslation();
  return (
    <div className="flex min-h-screen items-center justify-center text-content-secondary">
      <span role="status">{t("app.loading")}</span>
    </div>
  );
}

import { useTranslation } from "react-i18next";

type Page = "my_releases" | "all_releases" | "writers" | "settings";

/** Stands in for a page that a later step builds. */
export default function Placeholder({ page }: { page: Page }) {
  const { t } = useTranslation();
  return (
    <div className="max-w-2xl">
      <h1 className="mb-4xs text-3xl">{t(`nav.${page}`)}</h1>
      <p className="font-semibold">{t("placeholder.title")}</p>
      <p className="text-content-secondary">{t(`placeholder.${page}`)}</p>
    </div>
  );
}

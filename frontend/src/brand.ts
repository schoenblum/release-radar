import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { api } from "./api/client";

/** The institution's name and logo, in the current language. */
export function useBrand() {
  const { i18n } = useTranslation();
  const { data } = useQuery({ queryKey: ["brand"], queryFn: api.brand, staleTime: Infinity });
  const isJapanese = i18n.language === "ja";
  return {
    institutionName: data
      ? ((isJapanese ? data.institution_name_ja : null) ?? data.institution_name_en)
      : null,
    timezone: data?.timezone,
    logoUrl: data?.logo?.url ?? null,
    logoAlt: data?.logo
      ? ((isJapanese ? data.logo.alt_ja : null) ?? data.logo.alt_en ?? "")
      : "",
  };
}

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { api, http } from "../../api/client";
import type {
  AnalysisDimension,
  AnalysisOptions,
  AnalysisOverview,
  AnalysisReleases,
  AnalysisTop,
} from "../../api/types";
import { useAuth } from "../../auth";
import { useToast } from "../../components/Toast";
import { queryOf } from "./state";

/** The filter choices, pages and profiles. They change rarely, so one fetch serves a visit. */
export function useAnalysisOptions() {
  return useQuery({
    queryKey: ["analysis", "options"],
    queryFn: () => http.get<AnalysisOptions>("/analysis/options"),
    staleTime: 60_000,
  });
}

function useAddress(): URLSearchParams {
  const [params] = useSearchParams();
  return params;
}

export function useOverview() {
  const query = queryOf(useAddress());
  return useQuery({
    queryKey: ["analysis", "overview", query],
    queryFn: () => http.get<AnalysisOverview>(`/analysis/overview${query}`),
    placeholderData: keepPreviousData,
  });
}

export function useDimension(key: string) {
  const query = queryOf(useAddress());
  return useQuery({
    queryKey: ["analysis", "dimension", key, query],
    queryFn: () =>
      http.get<AnalysisDimension>(`/analysis/dimensions/${encodeURIComponent(key)}${query}`),
    placeholderData: keepPreviousData,
  });
}

export function useReleases() {
  const query = queryOf(useAddress());
  return useQuery({
    queryKey: ["analysis", "releases", query],
    queryFn: () => http.get<AnalysisReleases>(`/analysis/releases${query}`),
    placeholderData: keepPreviousData,
  });
}

export function useTop(dimension: string) {
  const query = queryOf(useAddress(), { dimension });
  return useQuery({
    queryKey: ["analysis", "top", query],
    queryFn: () => http.get<AnalysisTop>(`/analysis/top${query}`),
    placeholderData: keepPreviousData,
  });
}

/** Log scale per card, remembered per person (phase-2 brief §5.2). */
export function useLogScale(): [(key: string) => boolean, (key: string, on: boolean) => void] {
  const { t } = useTranslation();
  const { user, setUser } = useAuth();
  const toast = useToast();
  const saved = user?.preferences?.analysis_log_scale;
  const chosen = useMemo(() => saved ?? [], [saved]);
  const isOn = useCallback((key: string) => chosen.includes(key), [chosen]);
  const set = useCallback(
    (key: string, on: boolean) => {
      if (!user) return;
      const next = on ? [...new Set([...chosen, key])] : chosen.filter((item) => item !== key);
      // Show it straight away; the server keeps it for next time.
      setUser({ ...user, preferences: { ...user.preferences, analysis_log_scale: next } });
      void api
        .updateMe({ preferences: { analysis_log_scale: next } })
        .then((updated) => setUser(updated))
        .catch(() => toast({ text: t("analysis.not_saved") }));
    },
    [chosen, setUser, t, toast, user],
  );
  return [isOn, set];
}

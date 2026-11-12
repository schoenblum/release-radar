import { useQueries, useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { http } from "../../api/client";
import type {
  Checkpoint,
  CoreField,
  CustomField,
  Measure,
  ReleaseType,
  ResearchField,
  Unit,
  VocabularyItem,
  Writer,
} from "../../api/types";
import { useAuth } from "../../auth";
import { useBrand } from "../../brand";
import { formatDate } from "../../dates";
import { currentLanguage } from "../../i18n";
import { buildColumns, type GridColumn, type GridContext } from "./columns";

function useList<T>(path: string, queryKey: readonly unknown[]) {
  return useQuery({
    queryKey,
    queryFn: () => http.get<T[]>(path),
    refetchInterval: 60_000,
  });
}

/** Everything the columns depend on, with what Settings says about them. */
export function useGridColumns(): { columns: GridColumn[] | null; context: GridContext | null } {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const { timezone, displayTimeZones } = useBrand();
  const coreFields = useList<CoreField>("/core-fields", ["core-fields"]);
  const checkpoints = useList<Checkpoint>("/checkpoints", ["checkpoints"]);
  const measures = useList<Measure>("/measures", ["measures"]);
  const customFields = useList<CustomField>("/custom-fields", ["custom-fields"]);
  const units = useList<Unit>("/lists/units", ["lists", "units"]);
  const fields = useList<ResearchField>("/lists/fields", ["lists", "fields"]);
  const writers = useList<Writer>("/lists/writers", ["lists", "writers"]);
  const releaseTypes = useList<ReleaseType>("/lists/release_types", ["lists", "release_types"]);

  const vocabularyIds = useMemo(
    () => [
      ...new Set((customFields.data ?? []).flatMap((f) => (f.vocabulary_id ? [f.vocabulary_id] : []))),
    ],
    [customFields.data],
  );
  const vocabularies = useQueries({
    queries: vocabularyIds.map((id) => ({
      queryKey: ["lists", "vocabularies", id, "items"],
      queryFn: () => http.get<VocabularyItem[]>(`/lists/vocabularies/${id}/items`),
    })),
  });
  const vocabularyKey = vocabularies.map((query) => query.dataUpdatedAt).join();

  const language = i18n.language === "ja" ? "ja" : currentLanguage();
  const context = useMemo<GridContext | null>(() => {
    if (
      !user ||
      !coreFields.data ||
      !checkpoints.data ||
      !measures.data ||
      !customFields.data ||
      !units.data ||
      !fields.data ||
      !writers.data ||
      !releaseTypes.data
    ) {
      return null;
    }
    return {
      t,
      language,
      today: formatDate(new Date().toISOString(), timezone),
      canEdit: user.role === "admin" || user.role === "editor",
      userId: user.id,
      coreFields: coreFields.data,
      checkpoints: checkpoints.data,
      measures: measures.data,
      customFields: customFields.data,
      units: units.data,
      fields: fields.data,
      writers: writers.data,
      releaseTypes: releaseTypes.data,
      vocabularyItems: Object.fromEntries(
        vocabularyIds.map((id, index) => [id, vocabularies[index]?.data ?? []]),
      ),
      timezone: timezone ?? "Asia/Tokyo",
      displayZones: displayTimeZones,
    };
    // The queries array is new on each render. Its update times say when it changed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    t,
    language,
    timezone,
    displayTimeZones,
    user,
    coreFields.data,
    checkpoints.data,
    measures.data,
    customFields.data,
    units.data,
    fields.data,
    writers.data,
    releaseTypes.data,
    vocabularyIds,
    vocabularyKey,
  ]);
  const columns = useMemo(() => (context ? buildColumns(context) : null), [context]);
  return { columns, context };
}

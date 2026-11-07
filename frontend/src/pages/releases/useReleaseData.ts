import { keepPreviousData, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useMemo } from "react";

import { http } from "../../api/client";
import type {
  CrossrefStatus,
  HistoryEntry,
  Reading,
  Release,
  ReleaseCreated,
  ReleaseFilters,
  ReleasePage,
  ReleaseSaved,
} from "../../api/types";
import type { Commit } from "./columns";
import { filterQuery } from "./viewState";

export type DataView = "mine" | "all";

const LIST_KEY = ["releases", "list"];
// Releases added on this page, kept on screen even where the filters would hide them, so a
// new draft does not vanish the moment it is made. Shaped as a page, so edits reach it too.
const CREATED_KEY = [...LIST_KEY, "created"];
const NO_PAGE: ReleasePage = {
  items: [],
  total: 0,
  view_total: 0,
  has_writer_entry: false,
  academic_years: [],
};
export const DUE_KEY = ["releases", "due"];
const historyKey = (id: string) => ["releases", "history", id];
const PAGE_SIZE = 500;

export function useReleaseList(view: DataView, filters: ReleaseFilters = {}) {
  const query = filterQuery(filters);
  return useQuery({
    queryKey: [...LIST_KEY, view, query],
    queryFn: () =>
      http.get<ReleasePage>(`/releases?view=${view}&limit=${PAGE_SIZE}${query ? `&${query}` : ""}`),
    refetchInterval: 60_000,
    // The last view stays on screen while the next one loads, rather than a blank page.
    placeholderData: keepPreviousData,
  });
}

/** What was added here since the view last changed. */
export function useCreatedReleases(): Release[] {
  const { data } = useQuery({
    queryKey: CREATED_KEY,
    queryFn: () => NO_PAGE,
    enabled: false,
    initialData: NO_PAGE,
  });
  return data.items;
}

export function useReleaseHistory(id: string) {
  return useQuery({
    queryKey: historyKey(id),
    queryFn: () => http.get<HistoryEntry[]>(`/releases/${id}/history`),
  });
}

function mapPages(queryClient: QueryClient, change: (items: Release[]) => Release[]): void {
  queryClient.setQueriesData<ReleasePage>({ queryKey: LIST_KEY }, (page) =>
    page ? { ...page, items: change(page.items) } : page,
  );
}

export function latestRelease(queryClient: QueryClient, id: string): Release | undefined {
  for (const [, page] of queryClient.getQueriesData<ReleasePage>({ queryKey: LIST_KEY })) {
    const found = page?.items.find((item) => item.id === id);
    if (found) return found;
  }
  return undefined;
}

function storeRelease(queryClient: QueryClient, release: Release): void {
  mapPages(queryClient, (items) =>
    items.map((item) => (item.id === release.id ? release : item)),
  );
  void queryClient.invalidateQueries({ queryKey: historyKey(release.id) });
}

function storeReading(queryClient: QueryClient, releaseId: string, reading: Reading): void {
  mapPages(queryClient, (items) =>
    items.map((item) =>
      item.id === releaseId
        ? {
            ...item,
            readings: item.readings.map((row) => (row.id === reading.id ? reading : row)),
          }
        : item,
    ),
  );
  void queryClient.invalidateQueries({ queryKey: historyKey(releaseId) });
}

// One tidy-up after a burst of saves, such as a paste, rather than one per cell.
let dueRefresh: ReturnType<typeof setTimeout> | undefined;
function refreshDueSoon(queryClient: QueryClient): void {
  clearTimeout(dueRefresh);
  dueRefresh = setTimeout(() => void queryClient.invalidateQueries({ queryKey: DUE_KEY }), 300);
}

/** Saves wait their turn per release, so each one names the version the last one left. */
const queues = new Map<string, Promise<unknown>>();
function inTurn<T>(releaseId: string, work: () => Promise<T>): Promise<T> {
  const turn = (queues.get(releaseId) ?? Promise.resolve()).then(work, work);
  const settled = turn.catch(() => undefined);
  queues.set(releaseId, settled);
  void settled.then(() => {
    if (queues.get(releaseId) === settled) queues.delete(releaseId);
  });
  return turn;
}

export function useReleaseActions() {
  const queryClient = useQueryClient();
  return useMemo(() => {
    async function fetchPaper(releaseId: string, overwrite: boolean): Promise<CrossrefStatus> {
      const result = await http.post<{ status: CrossrefStatus; release: Release }>(
        `/releases/${releaseId}/crossref`,
        { overwrite },
      );
      storeRelease(queryClient, result.release);
      return result.status;
    }

    return {
      /** Apply one save. ``version`` overrides the one on file, to keep yours after a conflict. */
      save(releaseId: string, commit: Commit, version?: number): Promise<void> {
        return inTurn(releaseId, async () => {
          const release = latestRelease(queryClient, releaseId);
          if (commit.kind === "field") {
            const saved = await http.patch<ReleaseSaved>(`/releases/${releaseId}`, {
              field: commit.field,
              value: commit.value,
              version: version ?? release?.field_versions[commit.field] ?? 0,
            });
            storeRelease(queryClient, saved.release);
          } else if (commit.kind === "reading") {
            const reading = release?.readings.find((row) => row.id === commit.readingId);
            const saved = await http.patch<Reading>(`/readings/${commit.readingId}`, {
              ...commit.body,
              version: version ?? reading?.version ?? 0,
            });
            storeReading(queryClient, releaseId, saved);
          } else {
            const name = `custom_values.${commit.key}`;
            const saved = await http.patch<ReleaseSaved>(
              `/releases/${releaseId}/custom/${encodeURIComponent(commit.key)}`,
              { ...commit.body, version: version ?? release?.field_versions[name] ?? 0 },
            );
            storeRelease(queryClient, saved.release);
          }
          refreshDueSoon(queryClient);
        });
      },
      async create(payload: { title?: string; doi?: string }): Promise<ReleaseCreated> {
        const created = await http.post<ReleaseCreated>("/releases", payload);
        mapPages(queryClient, (items) => [created, ...items]);
        queryClient.setQueryData<ReleasePage>(CREATED_KEY, (page) => ({
          ...(page ?? NO_PAGE),
          items: [created, ...(page ?? NO_PAGE).items.filter((item) => item.id !== created.id)],
        }));
        void queryClient.invalidateQueries({ queryKey: LIST_KEY });
        return created;
      },
      /** Fills journal, paper title, date and authors. Only an explicit refetch overwrites. */
      fetchPaper,
      async remove(releaseId: string): Promise<void> {
        await http.delete(`/releases/${releaseId}`);
        mapPages(queryClient, (items) => items.filter((item) => item.id !== releaseId));
        refreshDueSoon(queryClient);
      },
      async restore(releaseId: string): Promise<void> {
        await http.post(`/releases/${releaseId}/restore`);
        await queryClient.invalidateQueries({ queryKey: LIST_KEY });
        refreshDueSoon(queryClient);
      },
      refreshList: () => void queryClient.invalidateQueries({ queryKey: LIST_KEY }),
      /** A new view shows what belongs in it, new releases included. */
      forgetCreated: () => {
        queryClient.setQueryData(CREATED_KEY, NO_PAGE);
      },
      storeRelease: (release: Release) => storeRelease(queryClient, release),
      storeReading: (releaseId: string, reading: Reading) =>
        storeReading(queryClient, releaseId, reading),
      refreshDue: () => refreshDueSoon(queryClient),
    };
  }, [queryClient]);
}

import { useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useMemo } from "react";

import { http } from "../../api/client";
import type {
  CrossrefStatus,
  HistoryEntry,
  Reading,
  Release,
  ReleaseCreated,
  ReleasePage,
  ReleaseSaved,
} from "../../api/types";
import type { Commit } from "./columns";

export type DataView = "mine" | "all";

const LIST_KEY = ["releases", "list"];
export const DUE_KEY = ["releases", "due"];
const historyKey = (id: string) => ["releases", "history", id];
const PAGE_SIZE = 500;

export function useReleaseList(view: DataView) {
  return useQuery({
    queryKey: [...LIST_KEY, view],
    queryFn: () => http.get<ReleasePage>(`/releases?view=${view}&limit=${PAGE_SIZE}`),
    refetchInterval: 60_000,
  });
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
      storeRelease: (release: Release) => storeRelease(queryClient, release),
      storeReading: (releaseId: string, reading: Reading) =>
        storeReading(queryClient, releaseId, reading),
      refreshDue: () => refreshDueSoon(queryClient),
    };
  }, [queryClient]);
}

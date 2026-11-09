import { useMemo, useState } from "react";

import type { Release } from "../../api/types";

const NONE: ReadonlySet<string> = new Set();

/**
 * Where a row that turns up while the page is open goes among the rows already placed: where
 * the chosen sort puts it, or else next to its neighbour in the server's order (newest first).
 */
function placeAmong(
  ids: string[],
  release: Release,
  list: Release[],
  byId: Map<string, Release>,
  compare: ((a: Release, b: Release) => number) | null,
  floor: number,
): string[] {
  let at: number;
  if (compare) {
    at = ids.findIndex(
      (id, index) => index >= floor && compare(release, byId.get(id) as Release) < 0,
    );
    if (at < 0) at = ids.length;
  } else {
    // After the nearest row above it in the server's order that is already placed.
    const placed = new Set(ids);
    const position = list.findIndex((item) => item.id === release.id);
    const above = list
      .slice(0, position)
      .reverse()
      .find((item) => placed.has(item.id));
    at = above ? ids.indexOf(above.id) + 1 : floor;
  }
  return [...ids.slice(0, Math.max(at, floor)), release.id, ...ids.slice(Math.max(at, floor))];
}

/**
 * Keeps rows where they are while someone works: changing a date must not make the row jump
 * away, even when the grid is sorted by date. The order is worked out afresh when the view,
 * its filters or the sort change. A release made in this tab (`pinned`) goes on top, where its
 * maker is looking; any other that turns up, such as one restored elsewhere, takes its place in
 * the order.
 */
export function useSteadyOrder(
  key: string,
  releases: Release[] | undefined,
  settled: boolean,
  compare: ((a: Release, b: Release) => number) | null,
  pinned: ReadonlySet<string> = NONE,
): Release[] {
  const [order, setOrder] = useState<{ key: string; ids: string[] }>({ key: "", ids: [] });
  const list = useMemo(() => releases ?? [], [releases]);
  if (releases && settled) {
    if (order.key !== key) {
      const sorted = compare ? [...list].sort(compare) : list;
      setOrder({ key, ids: sorted.map((release) => release.id) });
    } else {
      const incoming = new Set(list.map((release) => release.id));
      const known = new Set(order.ids);
      const differs =
        list.some((release) => !known.has(release.id)) ||
        order.ids.some((id) => !incoming.has(id));
      if (differs) {
        const byId = new Map(list.map((release) => [release.id, release]));
        const kept = order.ids.filter((id) => incoming.has(id));
        const keptSet = new Set(kept);
        const fresh = list.filter((release) => !keptSet.has(release.id));
        const onTop = fresh.filter((release) => pinned.has(release.id)).map((r) => r.id);
        let ids = [...onTop, ...kept];
        for (const release of fresh) {
          if (!pinned.has(release.id)) {
            ids = placeAmong(ids, release, list, byId, compare, onTop.length);
          }
        }
        setOrder({ key, ids });
      }
    }
  }
  return useMemo(() => {
    const byId = new Map(list.map((release) => [release.id, release]));
    return order.ids.flatMap((id) => {
      const release = byId.get(id);
      return release ? [release] : [];
    });
  }, [list, order.ids]);
}

import { useMemo, useState } from "react";

import type { Release } from "../../api/types";

/**
 * Keeps rows where they are while someone works: changing a date must not make the row jump
 * away, even when the grid is sorted by date. The order is worked out afresh when the view,
 * its filters or the sort change, and a new release goes on top.
 */
export function useSteadyOrder(
  key: string,
  releases: Release[] | undefined,
  settled: boolean,
  compare: ((a: Release, b: Release) => number) | null,
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
        const kept = order.ids.filter((id) => incoming.has(id));
        const keptSet = new Set(kept);
        const fresh = list.filter((release) => !keptSet.has(release.id)).map((r) => r.id);
        setOrder({ key, ids: [...fresh, ...kept] });
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

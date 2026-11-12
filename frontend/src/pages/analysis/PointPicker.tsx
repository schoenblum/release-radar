import { useEffect, useRef, useState, type RefObject } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { formatValue, type Language } from "./labels";
import { rankingRowId, recordLink } from "./RankingTable";

/**
 * Which release a dot is: click it (or near it) and a small window says, with a link to the
 * release's record (Daniel, 2026-11-12). A click, not hovering, so moving the pointer across a
 * chart shows nothing, and the window stays put to be clicked.
 *
 * Plot draws each dot of a mark marked `rr-pickable` as a circle whose data is its index into
 * the mark's data, which is how a circle leads back to its release.
 */
export interface PickablePoint {
  id: string;
  code: string | null;
  title: string | null;
  release_date: string;
  value: number;
  inferred: boolean;
}

export interface Picked {
  index: number;
  /** Where the dot is, in pixels from the chart's top left. */
  x: number;
  y: number;
}

/** What a chart reports each time it is drawn: a count, and the release asked for, if any. */
export interface Drawn {
  count: number;
  selected: Picked | null;
}

export const NOT_DRAWN: Drawn = { count: 0, selected: null };

const REACH = 14;

function indexOf(circle: Element): number | null {
  const data = (circle as unknown as { __data__?: unknown }).__data__;
  return typeof data === "number" ? data : null;
}

function centre(circle: Element, root: Element): { x: number; y: number } {
  const box = circle.getBoundingClientRect();
  const origin = root.getBoundingClientRect();
  return { x: box.left + box.width / 2 - origin.left, y: box.top + box.height / 2 - origin.top };
}

function circles(root: Element): Element[] {
  return [...root.querySelectorAll(".rr-pickable circle")];
}

/** The dot nearest a click, if one is within reach; of equally near ones, the first. */
function nearest(root: Element, clientX: number, clientY: number): Picked | null {
  const origin = root.getBoundingClientRect();
  let found: Picked | null = null;
  let best = REACH;
  for (const circle of circles(root)) {
    const index = indexOf(circle);
    if (index === null) continue;
    const at = centre(circle, root);
    const radius = circle.getBoundingClientRect().width / 2;
    const distance =
      Math.hypot(at.x + origin.left - clientX, at.y + origin.top - clientY) - radius;
    if (distance < best || (found === null && distance <= best)) {
      best = distance;
      found = { index, ...at };
    }
  }
  return found;
}

/**
 * Where a release's dot is, once a chart is drawn: for a release named from outside, such as
 * one in the address. Charts call it as they draw.
 */
export function locate(
  root: Element | null,
  points: PickablePoint[],
  selectedId: string | null | undefined,
): Picked | null {
  if (!root || !selectedId) return null;
  const index = points.findIndex((point) => point.id === selectedId);
  const circle = circles(root).find((item) => indexOf(item) === index);
  return circle && index >= 0 ? { index, ...centre(circle, root) } : null;
}

function mark(root: Element, index: number | null): void {
  for (const circle of circles(root)) {
    circle.classList.toggle("rr-picked", index !== null && indexOf(circle) === index);
  }
}

/**
 * Click handling for a chart's dots. A choice belongs to one drawing: drawn again (other
 * points, another width), the window from before goes, as it would point elsewhere.
 */
export function usePointPicker(root: RefObject<HTMLElement>, points: PickablePoint[], drawn: Drawn) {
  const [choice, setChoice] = useState<{ count: number; picked: Picked | null } | null>(null);
  const current = choice?.count === drawn.count ? choice.picked : drawn.selected;

  // The chosen dot stands out.
  useEffect(() => {
    if (root.current) mark(root.current, current?.index ?? null);
  }, [root, current, drawn]);

  return {
    picked: current && points[current.index] ? { ...current, point: points[current.index] } : null,
    onClick(event: { clientX: number; clientY: number; target: EventTarget }) {
      const element = root.current;
      if (!element) return;
      if ((event.target as Element).closest?.(".point-popover")) return;
      setChoice({ count: drawn.count, picked: nearest(element, event.clientX, event.clientY) });
    },
    close: () => setChoice({ count: drawn.count, picked: null }),
  };
}

/** The small window beside a clicked dot. */
export function PointPopover({
  point,
  x,
  y,
  width,
  decimals,
  measure,
  onClose,
  inRanking = false,
}: {
  point: PickablePoint;
  x: number;
  y: number;
  width: number;
  decimals: number;
  measure: string;
  onClose: () => void;
  /** On a measure's page: a link down to the release's row in the ranking. */
  inRanking?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.language === "ja" ? "ja" : "en";
  const box = useRef<HTMLDivElement>(null);
  const popoverWidth = Math.min(288, width);
  const left = Math.max(0, Math.min(x - popoverWidth / 2, width - popoverWidth));

  useEffect(() => {
    function onKey(event: KeyboardEvent): void {
      if (event.key === "Escape") onClose();
    }
    // A press anywhere outside the chart closes the window; inside it, the chart's own click
    // picks another dot or closes it.
    function onPress(event: PointerEvent): void {
      const chart = box.current?.parentElement;
      if (chart && !chart.contains(event.target as Node)) onClose();
    }
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPress);
    // The window itself takes the focus, not its link: a link focused by a script draws the
    // focus ring after a mouse click in Safari (Daniel, 2026-11-12). Tab reaches the link.
    box.current?.focus({ preventScroll: true });
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPress);
    };
  }, [onClose, point.id]);

  return (
    <div
      ref={box}
      className="point-popover"
      role="dialog"
      tabIndex={-1}
      aria-label={point.title ?? point.code ?? ""}
      style={{ left, top: y + 10, width: popoverWidth }}
    >
      <div className="flex items-start justify-between gap-4xs">
        <p className="text-xs text-content-secondary">
          {[point.code, point.release_date].filter(Boolean).join(" · ")}
        </p>
        <button
          type="button"
          className="point-popover-close"
          aria-label={t("data.close")}
          onClick={onClose}
        >
          ×
        </button>
      </div>
      <Link className="point-popover-title" to={recordLink(point.id)}>
        {point.title || t("data.no_title")}
      </Link>
      <p className="mt-5xs text-sm">
        {measure}: <span className="font-semibold tabular-nums">{formatValue(point.value, decimals, language)}</span>
        {point.inferred ? ` (${t("data.inferred")})` : ""}
      </p>
      {inRanking && (
        <button
          type="button"
          className="link-button mt-5xs text-sm"
          onClick={() => {
            const row = document.getElementById(rankingRowId(point.id));
            row?.scrollIntoView?.({ block: "center" });
            row?.querySelector<HTMLElement>("a")?.focus({ preventScroll: true });
          }}
        >
          {t("analysis.pick.in_ranking")}
        </button>
      )}
      <p className="mt-5xs text-xs text-content-secondary">{t("analysis.pick.open_hint")}</p>
    </div>
  );
}

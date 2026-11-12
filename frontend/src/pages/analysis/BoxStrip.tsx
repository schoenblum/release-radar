import * as Plot from "@observablehq/plot";
import { useEffect, useRef, useState, type RefObject } from "react";

import type { AnalysisBox, AnalysisPoint } from "../../api/types";
import { locate, NOT_DRAWN, PointPopover, usePointPicker, type Drawn } from "./PointPicker";

/**
 * A horizontal box of the analysed releases (quartiles, whiskers to the lowest and highest
 * value) with the shown releases as points above it (phase-2 brief §5.2). Drawn with Observable
 * Plot as two charts on one x scale: the points, packed so none hides another, then the box.
 * Clicking a point says which release it is.
 *
 * The production CSP allows no inline <style>. Plot adds one to each chart, so it is removed
 * before the chart reaches the page; the same rules live in index.css (`.rr-plot`).
 */
export interface BoxStripProps {
  box: AnalysisBox;
  points: AnalysisPoint[];
  logScale: boolean;
  /** Taller, with an axis: a dimension's own page. */
  large?: boolean;
  label: string;
  describe: (point: AnalysisPoint) => string;
  /** For the window a clicked point opens. */
  measure: string;
  decimals: number;
  /** A release to show as clicked, such as one named in the address. */
  selectedId?: string | null;
}

const FALLBACK_WIDTH = 320;
const MARGIN = 12;

export function useWidth(): [RefObject<HTMLDivElement>, number] {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(FALLBACK_WIDTH);
  useEffect(() => {
    const element = box.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver((entries) => {
      const measured = Math.floor(entries[0].contentRect.width);
      if (measured > 0) setWidth(measured);
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return [box, width];
}

export function withoutStyle<T extends Element>(chart: T): T {
  chart.querySelectorAll("style").forEach((element) => element.remove());
  return chart;
}

function radius(count: number, large: boolean): number {
  if (count > 150) return large ? 2.5 : 1.75;
  if (count > 60) return large ? 3 : 2.25;
  return large ? 4 : 3;
}

/**
 * How tall the points need to be, and how large each can be, so a pile of equal values (a
 * survey's 0s and 1s) stays inside the card: the tallest pile sets the height, up to a limit,
 * and beyond it the points get smaller (Daniel, 2026-11-12).
 */
export function packing(
  positions: number[],
  large: boolean,
): { r: number; height: number } {
  const most = large ? 220 : 120;
  const least = large ? 140 : 72;
  let r = radius(positions.length, large);
  for (let round = 0; round < 3; round += 1) {
    const piles = new Map<number, number>();
    for (const x of positions) {
      const bin = Math.floor(x / (2 * r));
      piles.set(bin, (piles.get(bin) ?? 0) + 1);
    }
    const tallest = Math.max(0, ...piles.values());
    const needed = tallest * 2 * r + 2 * r + 6;
    if (needed <= most) return { r, height: Math.max(least, needed) };
    r = Math.max(1, (most - 6) / (2 * (tallest + 1)));
  }
  return { r, height: most };
}

export default function BoxStrip({
  box,
  points,
  logScale,
  large = false,
  label,
  describe,
  measure,
  decimals,
  selectedId,
}: BoxStripProps) {
  const [holder, width] = useWidth();
  const target = useRef<HTMLDivElement>(null);
  const [drawn, setDrawn] = useState<Drawn>(NOT_DRAWN);
  const picker = usePointPicker(holder, points, drawn);

  useEffect(() => {
    const element = target.current;
    if (!element) return;
    const x: Plot.ScaleOptions = {
      type: logScale ? "symlog" : "linear",
      domain: [box.low, box.high === box.low ? box.low + 1 : box.high],
      nice: false,
    };
    const scale = Plot.scale({ x: { ...x, range: [MARGIN, width - MARGIN] } });
    const { r, height } = packing(
      points.map((point) => scale.apply(point.value) as number),
      large,
    );
    const shared = { width, marginLeft: MARGIN, marginRight: MARGIN };
    const dots = Plot.plot({
      ...shared,
      className: "rr-plot",
      height,
      marginTop: 4,
      marginBottom: 2,
      x: { ...x, axis: null },
      y: { axis: null },
      marks: [
        Plot.dotX(
          points,
          Plot.dodgeY("bottom", {
            x: "value",
            r,
            className: "rr-dots rr-pickable",
            title: describe,
          }),
        ),
      ],
    });
    const whiskers = Plot.plot({
      ...shared,
      className: "rr-plot",
      height: large ? 64 : 30,
      marginTop: 4,
      marginBottom: large ? 26 : 4,
      x: large ? { ...x, grid: false, tickFormat: "~s" } : { ...x, axis: null },
      y: { axis: null, domain: [0, 1] },
      marks: [
        Plot.ruleY([0.5], { x1: box.low, x2: box.high, className: "rr-whisker" }),
        Plot.ruleX([box.low, box.high], { y1: 0.25, y2: 0.75, className: "rr-whisker" }),
        Plot.rect([box], { x1: "q1", x2: "q3", y1: 0.05, y2: 0.95, className: "rr-box" }),
        Plot.ruleX([box.median], { y1: 0, y2: 1, strokeWidth: 3, className: "rr-median" }),
      ],
    });
    element.replaceChildren(withoutStyle(dots), withoutStyle(whiskers));
    const selected = locate(holder.current, points, selectedId);
    setDrawn((previous) => ({ count: previous.count + 1, selected }));
    return () => element.replaceChildren();
  }, [box, points, logScale, large, width, describe, holder, selectedId]);

  const { picked } = picker;
  return (
    // The chart says it all in words below it; clicking is an extra for those who point.
    <div ref={holder} className="rr-chart w-full" onClick={picker.onClick}>
      <div ref={target} role="img" aria-label={label} />
      {picked && (
        <PointPopover
          point={picked.point}
          x={picked.x}
          y={picked.y}
          width={width}
          decimals={decimals}
          measure={measure}
          onClose={picker.close}
          inRanking={large}
        />
      )}
    </div>
  );
}

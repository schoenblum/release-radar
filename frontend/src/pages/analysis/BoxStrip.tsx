import * as Plot from "@observablehq/plot";
import { useEffect, useRef, useState, type RefObject } from "react";

import type { AnalysisBox, AnalysisPoint } from "../../api/types";

/**
 * A horizontal box of the analysed releases (quartiles, whiskers to the lowest and highest
 * value) with the shown releases as points above it (phase-2 brief §5.2). Drawn with Observable
 * Plot as two charts on one x scale: the points, packed so none hides another, then the box.
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
}

const FALLBACK_WIDTH = 320;
const MARGIN = 12;

function useWidth(): [RefObject<HTMLDivElement>, number] {
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

function withoutStyle<T extends Element>(chart: T): T {
  chart.querySelectorAll("style").forEach((element) => element.remove());
  return chart;
}

function radius(count: number, large: boolean): number {
  if (count > 150) return large ? 2.5 : 1.75;
  if (count > 60) return large ? 3 : 2.25;
  return large ? 4 : 3;
}

export default function BoxStrip({ box, points, logScale, large = false, label, describe }: BoxStripProps) {
  const [holder, width] = useWidth();
  const target = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = target.current;
    if (!element) return;
    const x: Plot.ScaleOptions = {
      type: logScale ? "symlog" : "linear",
      domain: [box.low, box.high === box.low ? box.low + 1 : box.high],
      nice: false,
    };
    const shared = { width, marginLeft: MARGIN, marginRight: MARGIN };
    const dots = Plot.plot({
      ...shared,
      className: "rr-plot",
      height: large ? 140 : 72,
      marginTop: 4,
      marginBottom: 2,
      x: { ...x, axis: null },
      y: { axis: null },
      marks: [
        Plot.dotX(
          points,
          Plot.dodgeY("bottom", {
            x: "value",
            r: radius(points.length, large),
            className: "rr-dots",
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
    return () => element.replaceChildren();
  }, [box, points, logScale, large, width, describe]);

  return (
    <div ref={holder} className="w-full">
      <div ref={target} role="img" aria-label={label} />
    </div>
  );
}

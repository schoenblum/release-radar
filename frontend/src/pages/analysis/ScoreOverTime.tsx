import * as Plot from "@observablehq/plot";
import { useEffect, useRef, useState } from "react";

import type { AnalysisPoint, AnalysisYearMedian } from "../../api/types";
import { useWidth, withoutStyle } from "./BoxStrip";
import { NOT_DRAWN, PointPopover, usePointPicker, type Drawn } from "./PointPicker";

/**
 * The score over time (Daniel, 2026-11-12): a score compares a release with its neighbours, so
 * its median sits near 50 by design and a box says little. Instead, each shown release is a dot
 * by release date, and each academic year's median a line across that year's releases: whether
 * releases do better than those of the years before shows as the lines rising.
 */
const DAY = 86_400_000;

function utc(text: string): Date {
  return new Date(`${text}T00:00:00Z`);
}

export default function ScoreOverTime({
  points,
  years,
  label,
  measure,
  describe,
}: {
  points: AnalysisPoint[];
  years: AnalysisYearMedian[];
  label: string;
  measure: string;
  describe: (point: AnalysisPoint) => string;
}) {
  const [holder, width] = useWidth();
  const target = useRef<HTMLDivElement>(null);
  const [drawn, setDrawn] = useState<Drawn>(NOT_DRAWN);
  const picker = usePointPicker(holder, points, drawn);

  useEffect(() => {
    const element = target.current;
    if (!element) return;
    // A year with one release still gets a short line.
    const lines = years.map((year) => {
      const first = utc(year.first).getTime();
      const last = utc(year.last).getTime();
      const pad = first === last ? 7 * DAY : 0;
      return { ...year, x1: new Date(first - pad), x2: new Date(last + pad) };
    });
    const chart = Plot.plot({
      width,
      height: 200,
      className: "rr-plot",
      marginLeft: 32,
      marginRight: 12,
      marginTop: 10,
      marginBottom: 24,
      x: {
        type: "utc",
        label: null,
        ticks: Math.max(2, Math.floor(width / 110)),
        // Dates as everywhere else: year and month, in numbers.
        tickFormat: (date: Date) => date.toISOString().slice(0, 7),
      },
      y: { domain: [0, 100], ticks: [0, 50, 100], label: null, grid: true },
      marks: [
        Plot.link(lines, {
          x1: "x1",
          x2: "x2",
          y1: "median",
          y2: "median",
          strokeWidth: 3,
          className: "rr-year-median",
        }),
        Plot.dot(points, {
          x: (point: AnalysisPoint) => utc(point.release_date),
          y: "value",
          r: points.length > 150 ? 2 : 3,
          className: "rr-dots rr-pickable",
          title: describe,
        }),
      ],
    });
    element.replaceChildren(withoutStyle(chart));
    setDrawn((previous) => ({ count: previous.count + 1, selected: null }));
    return () => element.replaceChildren();
  }, [points, years, width, describe]);

  const { picked } = picker;
  return (
    <div ref={holder} className="rr-chart w-full" onClick={picker.onClick}>
      <div ref={target} role="img" aria-label={label} />
      {picked && (
        <PointPopover
          point={picked.point}
          x={picked.x}
          y={picked.y}
          width={width}
          decimals={0}
          measure={measure}
          onClose={picker.close}
        />
      )}
    </div>
  );
}

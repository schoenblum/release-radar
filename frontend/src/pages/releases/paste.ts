import type { Release } from "../../api/types";
import type { Commit, GridColumn } from "./columns";

export interface CellRange {
  top: number;
  left: number;
  bottom: number;
  right: number;
}

export interface PlannedSave {
  release: Release;
  column: GridColumn;
  /** What was pasted, shown in the cell until it has been saved. */
  text: string;
  commit: Commit;
}

export interface PlannedProblem {
  release: Release;
  column: GridColumn;
  text: string;
  code: string;
}

export interface PastePlan {
  saves: PlannedSave[];
  /** Validated cell by cell, so these cost only themselves (R7.5.2). */
  problems: PlannedProblem[];
  /** Cells that cannot be changed here, such as automatic numbers. */
  skipped: number;
  /** Pasted cells past the last row or column. */
  overflow: number;
}

/**
 * What a paste would do. One value fills the whole selected range. Several start at its top
 * left corner and take the room they need, as in a spreadsheet.
 */
export function planPaste(
  cells: string[][],
  range: CellRange,
  rows: Release[],
  columns: GridColumn[],
): PastePlan {
  const plan: PastePlan = { saves: [], problems: [], skipped: 0, overflow: 0 };
  const single = cells.length === 1 && cells[0].length === 1;
  const height = single ? range.bottom - range.top + 1 : cells.length;
  for (let offset = 0; offset < height; offset += 1) {
    const line = single ? null : cells[offset];
    const width = single ? range.right - range.left + 1 : (line?.length ?? 0);
    for (let across = 0; across < width; across += 1) {
      const release = rows[range.top + offset];
      const column = columns[range.left + across];
      if (!release || !column) {
        plan.overflow += 1;
        continue;
      }
      if (!column.isEditable(release)) {
        plan.skipped += 1;
        continue;
      }
      const text = single ? cells[0][0] : (line?.[across] ?? "");
      const parsed = column.parse(text, release);
      if (parsed.ok) plan.saves.push({ release, column, text, commit: parsed.commit });
      else plan.problems.push({ release, column, text, code: parsed.code });
    }
  }
  return plan;
}

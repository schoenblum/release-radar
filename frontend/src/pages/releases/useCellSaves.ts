import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import { ApiError } from "../../api/client";
import type { Release } from "../../api/types";
import type { Commit, GridColumn } from "./columns";

export interface PendingCell {
  status: "saving" | "saved" | "failed";
  /** What was typed, which stays on screen until it is saved or dropped (R7.5.5). */
  text: string;
  commit: Commit;
  /** Why it failed: an error code. */
  code?: string;
  /** Someone else changed it first: what it is now, for choosing which to keep (R3.3.3). */
  conflict?: { value: unknown; state?: string; version: number };
}

export type PendingCells = Record<string, Record<string, PendingCell>>;

export interface CellSave {
  release: Release;
  column: GridColumn;
  text: string;
  commit: Commit;
}

/** A value that cannot be saved as it stands, such as text in a number cell. */
export interface CellProblem {
  release: Release;
  column: GridColumn;
  text: string;
  code: string;
}

export interface SaveOutcome {
  saved: number;
  failed: number;
}

interface UndoEntry {
  /** The saves that put the cells back as they were. */
  commits: { releaseId: string; commit: Commit }[];
  /** Cells the group left unsaved, with what was typed: undo clears them too. */
  marks: { releaseId: string; columnId: string; text: string }[];
}

const SAVED_MARK_MS = 1200;

/** Saving cells: what is on its way, what failed and why, and what Undo can put back. */
export function useCellSaves(
  apply: (releaseId: string, commit: Commit, version?: number) => Promise<void>,
) {
  const [pending, setPending] = useState<PendingCells>({});
  const undoStack = useRef<UndoEntry[]>([]);
  const timers = useRef(new Set<ReturnType<typeof setTimeout>>());
  // Undo reads what is on screen now, not what was there when it was set up.
  const latestPending = useRef(pending);
  useLayoutEffect(() => {
    latestPending.current = pending;
  });

  useEffect(() => {
    const running = timers.current;
    return () => running.forEach(clearTimeout);
  }, []);

  const setCell = useCallback((releaseId: string, columnId: string, cell: PendingCell | null) => {
    setPending((current) => {
      const row = { ...current[releaseId] };
      if (cell) row[columnId] = cell;
      else delete row[columnId];
      const next = { ...current };
      if (Object.keys(row).length > 0) next[releaseId] = row;
      else delete next[releaseId];
      return next;
    });
  }, []);

  const clearMark = useCallback(
    (releaseId: string, columnId: string) => {
      const timer = setTimeout(() => {
        timers.current.delete(timer);
        setPending((current) =>
          current[releaseId]?.[columnId]?.status === "saved"
            ? (() => {
                const row = { ...current[releaseId] };
                delete row[columnId];
                const next = { ...current };
                if (Object.keys(row).length > 0) next[releaseId] = row;
                else delete next[releaseId];
                return next;
              })()
            : current,
        );
      }, SAVED_MARK_MS);
      timers.current.add(timer);
    },
    [],
  );

  const one = useCallback(
    async (
      releaseId: string,
      columnId: string,
      text: string,
      commit: Commit,
      version?: number,
    ): Promise<boolean> => {
      setCell(releaseId, columnId, { status: "saving", text, commit });
      try {
        await apply(releaseId, commit, version);
        setCell(releaseId, columnId, { status: "saved", text, commit });
        clearMark(releaseId, columnId);
        return true;
      } catch (error) {
        if (error instanceof ApiError && error.code === "conflict") {
          setCell(releaseId, columnId, {
            status: "failed",
            text,
            commit,
            code: "conflict",
            conflict: {
              value: error.body.current_value,
              state: error.body.current_state as string | undefined,
              version: Number(error.body.current_version),
            },
          });
        } else {
          const code = error instanceof ApiError ? error.code : "network";
          setCell(releaseId, columnId, { status: "failed", text, commit, code });
        }
        return false;
      }
    },
    [apply, clearMark, setCell],
  );

  const markProblem = useCallback(
    (item: CellProblem) => {
      setCell(item.release.id, item.column.id, {
        status: "failed",
        text: item.text,
        commit: { kind: "field", field: "", value: null },
        code: item.code,
      });
    },
    [setCell],
  );

  /**
   * Save a group of cells, and show the problems that came with it, such as a paste's.
   * Undo takes the whole group back in one go, unsaved cells included.
   */
  const save = useCallback(
    async (group: CellSave[], problems: CellProblem[] = []): Promise<SaveOutcome> => {
      problems.forEach(markProblem);
      const before = group.map((item) => ({
        releaseId: item.release.id,
        commit: item.column.snapshot(item.release),
      }));
      const results = await Promise.all(
        group.map((item) => one(item.release.id, item.column.id, item.text, item.commit)),
      );
      const commits = before.flatMap((entry, index) =>
        results[index] && entry.commit ? [{ releaseId: entry.releaseId, commit: entry.commit }] : [],
      );
      const marks = [
        ...group.filter((_, index) => !results[index]),
        ...problems,
      ].map((item) => ({ releaseId: item.release.id, columnId: item.column.id, text: item.text }));
      if (commits.length > 0 || marks.length > 0) undoStack.current.push({ commits, marks });
      const saved = results.filter(Boolean).length;
      return { saved, failed: results.length - saved };
    },
    [one, markProblem],
  );

  /** Put back the last group. Returns how many cells it restored, or null with nothing to undo. */
  const undo = useCallback(async (): Promise<number | null> => {
    for (;;) {
      const entry = undoStack.current.pop();
      if (!entry) return null;
      // A cell fixed or dropped since needs nothing, and a group with nothing left is skipped.
      const marks = entry.marks.filter(({ releaseId, columnId, text }) => {
        const cell = latestPending.current[releaseId]?.[columnId];
        return cell?.status === "failed" && cell.text === text;
      });
      if (entry.commits.length === 0 && marks.length === 0) continue;
      marks.forEach(({ releaseId, columnId }) => setCell(releaseId, columnId, null));
      await Promise.all(entry.commits.map(({ releaseId, commit }) => apply(releaseId, commit)));
      return entry.commits.length + marks.length;
    }
  }, [apply, setCell]);

  const drop = useCallback(
    (releaseId: string, columnId: string) => setCell(releaseId, columnId, null),
    [setCell],
  );

  /** After a conflict: this person's value wins, at the version someone else left. */
  const keepMine = useCallback(
    async (releaseId: string, columnId: string, cell: PendingCell) => {
      await one(releaseId, columnId, cell.text, cell.commit, cell.conflict?.version);
    },
    [one],
  );

  return { pending, save, undo, markProblem, drop, keepMine };
}

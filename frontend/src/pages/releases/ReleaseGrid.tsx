import {
  columnSizingFeature,
  columnVisibilityFeature,
  createColumnHelper,
  tableFeatures,
  useTable,
  type ColumnVisibilityState,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  memo,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ClipboardEvent,
  type KeyboardEvent,
  type MouseEvent,
  type ReactNode,
} from "react";
import { flushSync } from "react-dom";
import { useTranslation } from "react-i18next";

import { codeMessage } from "../../api/errors";
import type { Release, Unit } from "../../api/types";
import { useToast } from "../../components/Toast";
import CellEditor, { type Move } from "./CellEditor";
import { parseClipboard, toClipboard } from "./clipboard";
import { isVisible, type ColumnChoice, type GridColumn, type SortState, type Tone } from "./columns";
import { parseBoolean } from "./parse";
import { planPaste, type CellRange } from "./paste";
import type { PendingCell, PendingCells, useCellSaves } from "./useCellSaves";

const features = tableFeatures({ columnVisibilityFeature, columnSizingFeature });
const helper = createColumnHelper<typeof features, Release>();
const getRowId = (release: Release): string => release.id;

// Kept in step with .grid-cell and .grid-head-row in index.css.
const ROW_HEIGHT = 36;
const HEADER_HEIGHT = 48;
const NEW_ROW_HEIGHT = 52;
const OVERSCAN_ROWS = 10;

interface CellId {
  row: string;
  column: string;
}

interface Editing extends CellId {
  initial: string;
  replace: boolean;
}

const cellDomId = (cell: CellId): string => `cell-${cell.row}-${cell.column}`;
const headDomId = (column: string): string => `head-${column}`;

const TONE_CLASS: Record<Tone, string> = {
  due: "tone-due",
  na: "tone-na",
  later: "tone-later",
  muted: "tone-muted",
  plain: "",
};

function displayedValue(pending: PendingCell | undefined): pending is PendingCell {
  return !!pending && pending.status !== "saved";
}

/**
 * Where a cell's message fits: below the cell, or above it when the visible part of the grid
 * ends too soon, and from the cell's right edge near the right side. Measured, because the
 * grid scrolls inside itself and the page scrolls too. It only places the box, so it sets
 * the classes itself rather than rendering again.
 */
function useFittingPlace(box: React.RefObject<HTMLDivElement | null>, deps: unknown[]): void {
  useLayoutEffect(() => {
    const element = box.current;
    const cell = element?.parentElement;
    const frame = element?.closest<HTMLElement>(".grid-scroll");
    if (!element || !cell || !frame) return;
    const area = frame.getBoundingClientRect();
    const head = frame.querySelector("thead")?.getBoundingClientRect().height ?? 0;
    const own = element.getBoundingClientRect();
    const at = cell.getBoundingClientRect();
    const top = Math.max(area.top + head, 0);
    const bottom = Math.min(area.bottom, window.innerHeight);
    const right = Math.min(area.right, window.innerWidth);
    element.classList.toggle(
      "grid-message-above",
      at.bottom + own.height > bottom && at.top - own.height >= top,
    );
    element.classList.toggle(
      "grid-message-right",
      at.left + own.width > right && at.right - own.width >= area.left,
    );
    // Measured once per message: what it says decides its size.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}

function CellMessage({ pending, column }: { pending: PendingCell; column: GridColumn }) {
  const { t } = useTranslation();
  const box = useRef<HTMLDivElement>(null);
  useFittingPlace(box, [pending.code, pending.conflict?.version]);
  const className = "grid-message";
  if (pending.conflict) {
    const { value, state } = pending.conflict;
    const shown =
      state === "not_applicable"
        ? t("data.not_applicable")
        : value === null || value === ""
          ? t("conflict.empty")
          : typeof value === "object"
            ? JSON.stringify(value)
            : String(value);
    return (
      <div ref={box} role="alert" className={className}>
        <p>{t("conflict.message", { value: shown })}</p>
        <div className="mt-5xs flex gap-5xs">
          <button type="button" className="btn-small" data-action="keep">
            {t("conflict.keep_mine")}
          </button>
          <button type="button" className="btn-small" data-action="theirs">
            {t("conflict.use_theirs")}
          </button>
        </div>
      </div>
    );
  }
  return (
    <div ref={box} role="alert" className={className}>
      <p>
        {column.editor === "number" && pending.code === "field_invalid"
          ? t("data.not_a_number")
          : codeMessage(t, pending.code ?? "generic")}
      </p>
      <p className="text-content-secondary">{t("data.failed_hint")}</p>
    </div>
  );
}

interface RowProps {
  release: Release;
  index: number;
  columns: GridColumn[];
  offsets: number[];
  /** The columns of the selected range in this row, as [first, last]. */
  range: [number, number] | null;
  activeColumn: string | null;
  editing: Editing | null;
  pending: Record<string, PendingCell> | undefined;
  units: Unit[];
  onCommit: (text: string, move: Move, next?: EventTarget | null) => void;
  onPickResearcher: (record: { id: string; name: string } | null) => void;
  onCancel: (next?: EventTarget | null) => void;
}

/** Rows re-render on their own, so moving around a long list stays quick. */
const GridRow = memo(function GridRow({
  release,
  index,
  columns,
  offsets,
  range,
  activeColumn,
  editing,
  pending,
  units,
  onCommit,
  onPickResearcher,
  onCancel,
}: RowProps) {
  return (
    <tr role="row" aria-rowindex={index + 2} data-row={index}>
      {columns.map((column, position) => {
        const cellPending = pending?.[column.id];
        const shown = displayedValue(cellPending);
        const view = column.view(release);
        const isEditing = editing?.column === column.id;
        const isActive = activeColumn === column.id;
        const editable = column.isEditable(release);
        const inRange = range !== null && position >= range[0] && position <= range[1];
        const classes = [
          "grid-cell",
          column.frozen ? "grid-cell-frozen" : "",
          column.alignRight ? "text-right" : "",
          shown ? "" : TONE_CLASS[view.tone],
          inRange ? "in-range" : "",
          isActive ? "is-active" : "",
          isEditing ? "is-editing" : "",
          editable ? "" : "is-read-only",
          cellPending?.status === "saving" ? "is-saving" : "",
          cellPending?.status === "saved" ? "is-saved" : "",
          cellPending?.status === "failed" ? "is-failed" : "",
          isActive && cellPending?.status === "failed" ? "has-message" : "",
        ]
          .filter(Boolean)
          .join(" ");
        const text = shown ? cellPending.text : view.text;
        const checked = view.checked !== undefined;
        return (
          <td
            key={column.id}
            id={cellDomId({ row: release.id, column: column.id })}
            role="gridcell"
            aria-colindex={position + 1}
            aria-selected={inRange || isActive}
            aria-readonly={!editable}
            data-column={position}
            className={classes}
            title={isEditing ? undefined : (view.hint ?? (checked ? undefined : text || undefined))}
            style={column.frozen ? { left: offsets[position] } : undefined}
          >
            {isEditing && editing ? (
              <CellEditor
                column={column}
                release={release}
                units={units}
                initial={editing.initial}
                replace={editing.replace}
                onCommit={onCommit}
                onPickResearcher={onPickResearcher}
                onCancel={onCancel}
              />
            ) : checked ? (
              // Shows the value only: a click selects the cell, Space changes it.
              <input
                type="checkbox"
                tabIndex={-1}
                readOnly
                className="grid-check"
                disabled={!editable}
                aria-label={column.label}
                checked={shown ? parseBoolean(cellPending.text) === true : view.checked === true}
              />
            ) : column.id === "title" ? (
              <span className="grid-text grid-title">{text}</span>
            ) : (
              <span className="grid-text">{text}</span>
            )}
            {isActive && !isEditing && cellPending?.status === "failed" && (
              <CellMessage pending={cellPending} column={column} />
            )}
          </td>
        );
      })}
    </tr>
  );
});

export default function ReleaseGrid({
  rows,
  allColumns,
  choice,
  canEdit,
  saves,
  units,
  newRow,
  empty,
  sort = null,
  onSort,
  onOpen,
  onRefresh,
}: {
  rows: Release[];
  allColumns: GridColumn[];
  choice: ColumnChoice;
  canEdit: boolean;
  saves: ReturnType<typeof useCellSaves>;
  units: Unit[];
  newRow: ReactNode;
  empty: ReactNode;
  sort?: SortState | null;
  /** A header was clicked: sort by it, turn it round, or stop sorting. */
  onSort?: (columnId: string) => void;
  onOpen: (releaseId: string) => void;
  onRefresh: () => void;
}) {
  const { t } = useTranslation();
  const toast = useToast();

  const definitions = useMemo(
    () =>
      allColumns.map((column) =>
        helper.display({ id: column.id, header: column.label, size: column.width }),
      ),
    [allColumns],
  );
  const columnVisibility = useMemo<ColumnVisibilityState>(
    () => Object.fromEntries(allColumns.map((column) => [column.id, isVisible(column, choice)])),
    [allColumns, choice],
  );
  const table = useTable({
    features,
    columns: definitions,
    data: rows,
    getRowId,
    state: { columnVisibility },
  });
  const leaves = table.getVisibleLeafColumns();
  const leafIds = leaves.map((leaf) => leaf.id).join("|");
  const columns = useMemo(() => {
    const byId = new Map(allColumns.map((column) => [column.id, column]));
    return leafIds
      .split("|")
      .map((id) => byId.get(id))
      .filter((column): column is GridColumn => !!column);
  }, [allColumns, leafIds]);

  const offsets = useMemo(() => {
    let left = 0;
    return columns.map((column) => {
      const start = left;
      if (column.frozen) left += column.width;
      return start;
    });
  }, [columns]);
  const frozenWidth = columns.reduce((sum, column) => sum + (column.frozen ? column.width : 0), 0);
  const totalWidth = columns.reduce((sum, column) => sum + column.width, 0);
  const headHeight = HEADER_HEIGHT + (newRow ? NEW_ROW_HEIGHT : 0);

  const scroller = useRef<HTMLDivElement>(null);
  const catcher = useRef<HTMLTextAreaElement>(null);
  const clicking = useRef(false);
  // How the last press came: a mouse, a pen or a finger.
  const pointer = useRef("mouse");
  // This project does not use the React Compiler, which is what the rule protects.
  // eslint-disable-next-line react-hooks/incompatible-library
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scroller.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: OVERSCAN_ROWS,
    scrollMargin: headHeight,
    scrollPaddingStart: headHeight,
    getItemKey: (index) => rows[index]?.id ?? index,
  });

  const [active, setActive] = useState<CellId | null>(null);
  const [anchor, setAnchor] = useState<CellId | null>(null);
  const [editing, setEditing] = useState<Editing | null>(null);
  // A column heading chosen by keyboard, where Enter sorts (the ARIA grid pattern): up from the
  // first row, as the headings are no stops for Tab of their own.
  const [heading, setHeading] = useState<string | null>(null);
  // Where the selection was before it was let go, so the arrow keys carry on from there.
  const lastActive = useRef<CellId | null>(null);

  const rowIndex = useMemo(() => new Map(rows.map((row, index) => [row.id, index])), [rows]);
  const columnIndex = useMemo(
    () => new Map(columns.map((column, index) => [column.id, index])),
    [columns],
  );

  const range = useMemo<CellRange | null>(() => {
    if (!active) return null;
    const row = rowIndex.get(active.row);
    const column = columnIndex.get(active.column);
    if (row === undefined || column === undefined) return null;
    const anchorRow = (anchor && rowIndex.get(anchor.row)) ?? row;
    const anchorColumn = (anchor && columnIndex.get(anchor.column)) ?? column;
    return {
      top: Math.min(row, anchorRow),
      bottom: Math.max(row, anchorRow),
      left: Math.min(column, anchorColumn),
      right: Math.max(column, anchorColumn),
    };
  }, [active, anchor, rowIndex, columnIndex]);

  const rangeLeft = range?.left;
  const rangeRight = range?.right;
  const rangeColumns = useMemo<[number, number] | null>(
    () =>
      rangeLeft === undefined || rangeRight === undefined ? null : [rangeLeft, rangeRight],
    [rangeLeft, rangeRight],
  );

  const moveTo = useCallback(
    (row: number, column: number, extend = false) => {
      const release = rows[Math.max(0, Math.min(rows.length - 1, row))];
      const target = columns[Math.max(0, Math.min(columns.length - 1, column))];
      if (!release || !target) return;
      const next = { row: release.id, column: target.id };
      setHeading(null);
      setActive(next);
      if (!extend) setAnchor(next);
    },
    [rows, columns],
  );

  // Bring a heading chosen by keyboard into view, past the frozen columns.
  useEffect(() => {
    if (heading) {
      document.getElementById(headDomId(heading))?.scrollIntoView({ block: "nearest", inline: "nearest" });
    }
  }, [heading]);

  // Bring the selected cell into view. Scroll padding keeps it clear of the frozen columns.
  useEffect(() => {
    if (!active) return;
    const index = rowIndex.get(active.row);
    if (index !== undefined) virtualizer.scrollToIndex(index, { align: "auto" });
    document
      .getElementById(cellDomId(active))
      ?.scrollIntoView({ block: "nearest", inline: "nearest" });
    // Only when the selection moves, not whenever the list refreshes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  const focusGrid = useCallback(() => {
    scroller.current?.focus({ preventScroll: true });
  }, []);

  /** After an editor closes. If it closed because focus went somewhere else, it stays there. */
  const refocus = useCallback(
    (next?: EventTarget | null) => {
      if (!next || next === scroller.current) focusGrid();
    },
    [focusGrid],
  );

  const letGo = useCallback(() => {
    if (active) lastActive.current = active;
    setActive(null);
    setAnchor(null);
  }, [active]);

  const commitCell = useCallback(
    (release: Release, column: GridColumn, text: string) => {
      const parsed = column.parse(text, release);
      if (parsed.ok) void saves.save([{ release, column, text, commit: parsed.commit }]);
      // Undo drops it again, as it would a value that was saved.
      else void saves.save([], [{ release, column, text, code: parsed.code }]);
    },
    [saves],
  );

  const startEditing = useCallback(
    (cell: CellId, replace: boolean, text?: string) => {
      const index = rowIndex.get(cell.row);
      const release = index === undefined ? undefined : rows[index];
      const column = columns[columnIndex.get(cell.column) ?? -1];
      if (!release || !column || !column.isEditable(release)) return;
      if (column.editor === "boolean" || column.editor === "none") return;
      const failed = saves.pending[release.id]?.[column.id];
      const initial =
        text ?? (failed?.status === "failed" ? failed.text : column.editText(release));
      // Synchronously, so the editor has focus before the next key arrives.
      flushSync(() => setEditing({ ...cell, initial, replace }));
    },
    [rows, columns, rowIndex, columnIndex, saves.pending],
  );

  // Editors get callbacks that never change, so opening one re-renders only its own row.
  const latest = useRef({ editing, rows, columns, rowIndex, columnIndex, saves, commitCell, moveTo });
  useLayoutEffect(() => {
    latest.current = { editing, rows, columns, rowIndex, columnIndex, saves, commitCell, moveTo };
  });

  const onCommit = useCallback(
    (text: string, move: Move, next?: EventTarget | null) => {
      const now = latest.current;
      setEditing(null);
      if (now.editing) {
        const index = now.rowIndex.get(now.editing.row);
        const position = now.columnIndex.get(now.editing.column);
        if (index !== undefined && position !== undefined) {
          const release = now.rows[index];
          const column = now.columns[position];
          const unchanged =
            text === now.editing.initial && now.saves.pending[release.id]?.[column.id] === undefined;
          if (!unchanged) now.commitCell(release, column, text);
          if (move.rows !== 0 || move.columns !== 0) {
            now.moveTo(index + move.rows, position + move.columns);
          }
        }
      }
      refocus(next);
    },
    [refocus],
  );

  const onCancel = useCallback(
    (next?: EventTarget | null) => {
      setEditing(null);
      refocus(next);
    },
    [refocus],
  );

  const onPickResearcher = useCallback(
    (record: { id: string; name: string } | null) => {
      const now = latest.current;
      setEditing(null);
      if (now.editing) {
        const index = now.rowIndex.get(now.editing.row);
        const position = now.columnIndex.get(now.editing.column);
        if (index !== undefined && position !== undefined) {
          void now.saves.save([
            {
              release: now.rows[index],
              column: now.columns[position],
              text: record?.name ?? "",
              commit: { kind: "field", field: "researcher_id", value: record?.id ?? null },
            },
          ]);
          now.moveTo(index + 1, position);
        }
      }
      focusGrid();
    },
    [focusGrid],
  );

  function toggle(release: Release, column: GridColumn): void {
    if (!column.isEditable(release)) return;
    const pending = saves.pending[release.id]?.[column.id];
    const now = displayedValue(pending)
      ? parseBoolean(pending.text) === true
      : column.view(release).checked === true;
    commitCell(release, column, now ? "" : "✓");
  }

  async function runUndo(): Promise<void> {
    try {
      const count = await saves.undo();
      if (count !== null) toast({ text: t("data.undid", { count }) });
    } catch {
      toast({ text: t("data.undo_failed") });
    }
  }

  function clearRange(): void {
    if (!range) return;
    const group = [];
    for (let row = range.top; row <= range.bottom; row += 1) {
      for (let position = range.left; position <= range.right; position += 1) {
        const release = rows[row];
        const column = columns[position];
        if (!release || !column || !column.isEditable(release)) continue;
        const parsed = column.parse("", release);
        if (parsed.ok) group.push({ release, column, text: "", commit: parsed.commit });
      }
    }
    if (group.length > 0) void saves.save(group);
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>): void {
    if (editing || event.nativeEvent.isComposing) return;
    if (event.target !== scroller.current && event.target !== catcher.current) return;
    // Safari offers copy and paste only where something can be edited. While Cmd or Ctrl is
    // held, this holds the focus, so the clipboard works the same in every browser.
    if ((event.key === "Meta" || event.key === "Control") && catcher.current) {
      catcher.current.value = " ";
      catcher.current.focus({ preventScroll: true });
      catcher.current.select();
      return;
    }
    if (heading !== null) {
      onHeadingKey(event, heading);
      return;
    }
    if (!active || !range) {
      if (rows.length > 0 && event.key.startsWith("Arrow")) {
        event.preventDefault();
        const last = lastActive.current;
        const row = last ? rowIndex.get(last.row) : undefined;
        const column = last ? columnIndex.get(last.column) : undefined;
        moveTo(row ?? 0, column ?? 0);
      }
      return;
    }
    const row = rowIndex.get(active.row);
    const position = columnIndex.get(active.column);
    if (row === undefined || position === undefined) return;
    const release = rows[row];
    const column = columns[position];
    const command = event.metaKey || event.ctrlKey;

    if (command) {
      if (event.key.toLowerCase() === "z" && !event.shiftKey && canEdit) {
        event.preventDefault();
        void runUndo();
      }
      return;
    }
    switch (event.key) {
      case "ArrowDown":
      case "ArrowUp":
      case "ArrowLeft":
      case "ArrowRight":
        event.preventDefault();
        if (event.key === "ArrowUp" && row === 0 && !event.shiftKey && onSort) {
          letGo();
          setHeading(column.id);
          return;
        }
        moveTo(
          row + (event.key === "ArrowDown" ? 1 : event.key === "ArrowUp" ? -1 : 0),
          position + (event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0),
          event.shiftKey,
        );
        return;
      case "Tab": {
        const backwards = event.shiftKey;
        const atEdge = backwards
          ? row === 0 && position === 0
          : row === rows.length - 1 && position === columns.length - 1;
        // Past the last cell, Tab leaves the grid, so a keyboard is never trapped in it.
        if (atEdge) return;
        event.preventDefault();
        if (!backwards && position === columns.length - 1) moveTo(row + 1, 0);
        else if (backwards && position === 0) moveTo(row - 1, columns.length - 1);
        else moveTo(row, position + (backwards ? -1 : 1));
        return;
      }
      case "Home":
        event.preventDefault();
        moveTo(row, 0, event.shiftKey);
        return;
      case "End":
        event.preventDefault();
        moveTo(row, columns.length - 1, event.shiftKey);
        return;
      case "Enter":
        event.preventDefault();
        if (event.shiftKey || column.editor === "none") onOpen(release.id);
        else if (column.editor === "boolean") toggle(release, column);
        else startEditing(active, false);
        return;
      case "F2":
        event.preventDefault();
        startEditing(active, false);
        return;
      case "Escape":
        if (saves.pending[release.id]?.[column.id]?.status === "failed") {
          saves.drop(release.id, column.id);
        } else if (range.top !== range.bottom || range.left !== range.right) {
          setAnchor(active);
        } else {
          // Nothing selected any more, so nothing is pasted over by mistake.
          letGo();
        }
        return;
      case "Backspace": {
        event.preventDefault();
        // A value that could not be saved is still being typed: Backspace takes off its last
        // character, so a slip like 31 for 30 is corrected rather than typed again.
        const failed = saves.pending[release.id]?.[column.id];
        const single = range.top === range.bottom && range.left === range.right;
        if (single && failed?.status === "failed") {
          startEditing(active, false, failed.text.slice(0, -1));
        } else {
          clearRange();
        }
        return;
      }
      case "Delete":
        event.preventDefault();
        clearRange();
        return;
      case " ":
        if (column.editor === "boolean") {
          event.preventDefault();
          toggle(release, column);
          return;
        }
        break;
      default:
        break;
    }
    // Any other key that writes something starts editing, and lands in the editor by itself.
    if ((event.key.length === 1 || event.key === "Process") && !event.altKey) {
      startEditing(active, true);
    }
  }

  /** On a heading: arrows along the headings or back down, Enter or Space sorts, Esc leaves. */
  function onHeadingKey(event: KeyboardEvent<HTMLDivElement>, column: string): void {
    const position = columnIndex.get(column) ?? 0;
    const along = (to: number) => {
      event.preventDefault();
      const target = columns[Math.max(0, Math.min(columns.length - 1, to))];
      if (target) setHeading(target.id);
    };
    switch (event.key) {
      case "ArrowLeft":
        along(position - 1);
        return;
      case "ArrowRight":
        along(position + 1);
        return;
      case "Home":
        along(0);
        return;
      case "End":
        along(columns.length - 1);
        return;
      case "ArrowDown":
        event.preventDefault();
        if (rows.length > 0) moveTo(0, position);
        return;
      case "Enter":
      case " ":
        event.preventDefault();
        onSort?.(column);
        return;
      case "Escape":
        setHeading(null);
        return;
      default:
        return;
    }
  }

  /** Only the grid's own: a paste or copy in the new-release box or an editor is theirs. */
  function isForTheGrid(event: ClipboardEvent<HTMLDivElement>): boolean {
    return event.target === scroller.current || event.target === catcher.current;
  }

  function onPaste(event: ClipboardEvent<HTMLDivElement>): void {
    if (!isForTheGrid(event) || editing || !range || !canEdit) return;
    event.preventDefault();
    const cells = parseClipboard(event.clipboardData.getData("text/plain"));
    const plan = planPaste(cells, range, rows, columns);
    void saves.save(plan.saves, plan.problems).then((outcome) => {
      const invalid = outcome.failed + plan.problems.length;
      toast({
        text: [
          invalid > 0
            ? t("data.paste_result", { saved: outcome.saved, invalid })
            : t("data.paste_saved", { count: outcome.saved }),
          plan.skipped > 0 ? t("data.paste_skipped", { count: plan.skipped }) : "",
          plan.overflow > 0 ? t("data.paste_overflow", { count: plan.overflow }) : "",
        ]
          .filter(Boolean)
          .join(" "),
        undo: outcome.saved > 0 || invalid > 0 ? () => void runUndo() : undefined,
      });
    });
  }

  function onCopy(event: ClipboardEvent<HTMLDivElement>): void {
    if (!isForTheGrid(event) || editing || !range) return;
    event.preventDefault();
    const lines: string[][] = [];
    for (let row = range.top; row <= range.bottom; row += 1) {
      const line: string[] = [];
      for (let position = range.left; position <= range.right; position += 1) {
        const release = rows[row];
        const column = columns[position];
        if (release && column) line.push(column.editText(release));
      }
      lines.push(line);
    }
    event.clipboardData.setData("text/plain", toClipboard(lines));
  }

  function cellAt(target: EventTarget): { release: Release; column: GridColumn } | null {
    const element = target as HTMLElement;
    const cell = element.closest<HTMLElement>("td[data-column]");
    const row = cell?.closest<HTMLElement>("tr[data-row]");
    if (!cell || !row) return null;
    const release = rows[Number(row.dataset.row)];
    const column = columns[Number(cell.dataset.column)];
    return release && column ? { release, column } : null;
  }

  function onMouseDown(event: MouseEvent<HTMLTableSectionElement>): void {
    const element = event.target as HTMLElement;
    if (element.closest(".grid-editor, .picker, .grid-message")) return;
    const found = cellAt(event.target);
    if (!found) return;
    const cell = { row: found.release.id, column: found.column.id };
    clicking.current = true;
    setActive(cell);
    if (!event.shiftKey) setAnchor(cell);
    // Keep the browser from selecting text while a range is being dragged. Focus moving to
    // the grid is what closes an open editor, and saves it.
    event.preventDefault();
    focusGrid();
    clicking.current = false;
  }

  function onMouseOver(event: MouseEvent<HTMLTableSectionElement>): void {
    if (event.buttons !== 1 || editing) return;
    const found = cellAt(event.target);
    if (found) setActive({ row: found.release.id, column: found.column.id });
  }

  /** The same in every cell: one click selects, a double click opens the full record. */
  function onDoubleClick(event: MouseEvent<HTMLTableSectionElement>): void {
    const element = event.target as HTMLElement;
    if (element.closest("[data-action], .grid-editor, .picker, .grid-message")) return;
    const found = cellAt(event.target);
    if (found) onOpen(found.release.id);
  }

  function onClick(event: MouseEvent<HTMLTableSectionElement>): void {
    const element = event.target as HTMLElement;
    const action = element.closest<HTMLElement>("[data-action]")?.dataset.action;
    const found = cellAt(event.target);
    if (!found) return;
    const { release, column } = found;
    if (!action) {
      // A finger has no keyboard to type into a selected cell, so a tap opens the record.
      if (pointer.current === "touch" && !element.closest(".grid-editor, .picker")) {
        onOpen(release.id);
      }
      return;
    }
    const pending = saves.pending[release.id]?.[column.id];
    if (action === "keep" && pending) void saves.keepMine(release.id, column.id, pending);
    if (action === "theirs") {
      saves.drop(release.id, column.id);
      onRefresh();
    }
  }

  const items = virtualizer.getVirtualItems();
  const before = items.length > 0 ? items[0].start - headHeight : 0;
  const after =
    items.length > 0
      ? virtualizer.getTotalSize() - (items[items.length - 1].end - headHeight)
      : 0;
  const coreRows = table.getRowModel().rows;
  const pendingByRow: PendingCells = saves.pending;

  return (
    <div
      ref={scroller}
      className="grid-scroll"
      role="grid"
      aria-label={t("data.grid_label")}
      aria-rowcount={rows.length + 1}
      aria-colcount={columns.length}
      aria-multiselectable
      aria-activedescendant={
        active ? cellDomId(active) : heading ? headDomId(heading) : undefined
      }
      aria-describedby="grid-keys"
      tabIndex={0}
      style={{ scrollPaddingLeft: frozenWidth, scrollPaddingTop: headHeight }}
      onKeyDown={onKeyDown}
      onKeyUp={(event) => {
        if ((event.key === "Meta" || event.key === "Control") && event.target === catcher.current) {
          focusGrid();
        }
      }}
      onPaste={onPaste}
      onCopy={onCopy}
      onFocus={(event) => {
        // Typing a new release lets go of the selection, so a paste there lands there.
        if ((event.target as HTMLElement).closest(".grid-new-row")) {
          letGo();
          return;
        }
        // Arriving by Tab starts at the first cell. A click has chosen its own.
        if (event.target === scroller.current && !active && !clicking.current && rows.length > 0) {
          moveTo(0, 0);
        }
      }}
    >
      <p id="grid-keys" className="sr-only">
        {t("data.grid_keys")}
      </p>
      {/* Editable on purpose: browsers can turn Paste off for a read-only field. */}
      <textarea ref={catcher} className="sr-only" tabIndex={-1} aria-hidden="true" />
      <table className="grid-table" role="presentation" style={{ width: totalWidth }}>
        <colgroup>
          {columns.map((column) => (
            <col key={column.id} style={{ width: column.width }} />
          ))}
        </colgroup>
        <thead role="rowgroup">
          <tr role="row" aria-rowindex={1} className="grid-head-row">
            {columns.map((column, position) => {
              const sorted = sort?.column === column.id ? sort : null;
              return (
                <th
                  key={column.id}
                  id={headDomId(column.id)}
                  role="columnheader"
                  aria-colindex={position + 1}
                  aria-sort={sorted ? (sorted.desc ? "descending" : "ascending") : undefined}
                  title={column.label}
                  className={[
                    column.frozen ? "grid-head-frozen" : "",
                    column.alignRight ? "text-right" : "",
                    heading === column.id ? "is-active" : "",
                  ].join(" ")}
                  style={column.frozen ? { left: offsets[position] } : undefined}
                >
                  {onSort ? (
                    <button
                      type="button"
                      // The grid is a single stop for Tab: the keyboard reaches a heading with
                      // the up arrow from the first row instead.
                      tabIndex={-1}
                      className="grid-sort"
                      title={t("data.sort_hint", { column: column.label })}
                      onClick={() => onSort(column.id)}
                    >
                      <span className="grid-sort-label">{column.label}</span>
                      {sorted && (
                        <span aria-hidden="true" className="grid-sort-mark">
                          {sorted.desc ? "▼" : "▲"}
                        </span>
                      )}
                    </button>
                  ) : (
                    column.label
                  )}
                </th>
              );
            })}
          </tr>
          {newRow && (
            <tr className="grid-new-row">
              <th colSpan={columns.length} className="grid-new-cell">
                {newRow}
              </th>
            </tr>
          )}
        </thead>
        <tbody
          role="rowgroup"
          onPointerDown={(event) => {
            pointer.current = event.pointerType;
          }}
          onMouseDown={onMouseDown}
          onMouseOver={onMouseOver}
          onDoubleClick={onDoubleClick}
          onClick={onClick}
        >
          {before > 0 && (
            <tr aria-hidden="true">
              <td colSpan={columns.length} style={{ height: before }} />
            </tr>
          )}
          {items.map((item) => {
            const coreRow = coreRows[item.index];
            if (!coreRow) return null;
            const release = coreRow.original;
            const inRows = range && item.index >= range.top && item.index <= range.bottom;
            return (
              <GridRow
                key={release.id}
                release={release}
                index={item.index}
                columns={columns}
                offsets={offsets}
                range={inRows ? rangeColumns : null}
                activeColumn={active?.row === release.id ? active.column : null}
                editing={editing?.row === release.id ? editing : null}
                pending={pendingByRow[release.id]}
                units={units}
                onCommit={onCommit}
                onPickResearcher={onPickResearcher}
                onCancel={onCancel}
              />
            );
          })}
          {after > 0 && (
            <tr aria-hidden="true">
              <td colSpan={columns.length} style={{ height: after }} />
            </tr>
          )}
        </tbody>
      </table>
      {rows.length === 0 && <div className="grid-empty">{empty}</div>}
    </div>
  );
}

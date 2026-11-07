import { useRef, useState, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

import type { Release, Unit } from "../../api/types";
import type { GridColumn } from "./columns";
import ResearcherPicker from "./ResearcherPicker";

export type Move = { rows: number; columns: number };

export interface CellEditorProps {
  column: GridColumn;
  release: Release;
  units: Unit[];
  initial: string;
  /** Started by typing: the first key replaces what is there, and arrow keys move on. */
  replace: boolean;
  onCommit: (text: string, move: Move) => void;
  onPickResearcher: (record: { id: string; name: string } | null) => void;
  onCancel: () => void;
}

/**
 * The editor inside a grid cell. It closes on Enter, Tab or clicking away, and never checks
 * anything itself: what cannot be saved comes back as a message on the cell, without holding
 * up anything else (R7.5.5).
 */
export default function CellEditor({
  column,
  release,
  units,
  initial,
  replace,
  onCommit,
  onPickResearcher,
  onCancel,
}: CellEditorProps) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState(initial);
  const finished = useRef(false);

  function commit(move: Move): void {
    if (finished.current) return;
    finished.current = true;
    onCommit(draft, move);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement | HTMLSelectElement>): void {
    // A key that settles a Japanese input is for the input method.
    if (event.nativeEvent.isComposing) return;
    event.stopPropagation();
    if (event.key === "Enter") {
      event.preventDefault();
      commit({ rows: event.shiftKey ? -1 : 1, columns: 0 });
    } else if (event.key === "Tab") {
      event.preventDefault();
      commit({ rows: 0, columns: event.shiftKey ? -1 : 1 });
    } else if (event.key === "Escape") {
      event.preventDefault();
      finished.current = true;
      onCancel();
    } else if (replace && column.editor !== "select") {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        commit({ rows: event.key === "ArrowDown" ? 1 : -1, columns: 0 });
      }
    }
  }

  if (column.editor === "researcher") {
    return (
      <ResearcherPicker
        authors={release.authors}
        units={units}
        hasValue={release.researcher_id !== null}
        autoFocus
        onPick={onPickResearcher}
        onClear={() => onPickResearcher(null)}
        onCancel={onCancel}
        onLeave={(backwards) => onCommit(initial, { rows: 0, columns: backwards ? -1 : 1 })}
      />
    );
  }

  if (column.editor === "select") {
    const labels = column.options.map((option) => option.label);
    return (
      <select
        ref={(element) => {
          if (element && document.activeElement !== element) element.focus();
        }}
        className="grid-editor"
        aria-label={column.label}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={onKeyDown}
        onBlur={() => commit({ rows: 0, columns: 0 })}
      >
        <option value="">{t("common.none")}</option>
        {/* An entry retired since it was chosen still shows here, and stays unless changed. */}
        {initial && !labels.includes(initial) && <option value={initial}>{initial}</option>}
        {labels.map((label) => (
          <option key={label} value={label}>
            {label}
          </option>
        ))}
      </select>
    );
  }

  return (
    <input
      // Mounted and focused inside the keystroke that opened it, so that fast typing and an
      // input method's composition land here instead of being lost.
      ref={(element) => {
        if (!element || document.activeElement === element) return;
        element.focus();
        if (replace) element.select();
        else element.setSelectionRange(element.value.length, element.value.length);
      }}
      className={column.alignRight ? "grid-editor text-right" : "grid-editor"}
      aria-label={column.label}
      inputMode={column.editor === "number" ? "decimal" : undefined}
      placeholder={column.editor === "date" ? "YYYY-MM-DD" : undefined}
      value={draft}
      onChange={(event) => setDraft(event.target.value)}
      onKeyDown={onKeyDown}
      onBlur={() => commit({ rows: 0, columns: 0 })}
    />
  );
}

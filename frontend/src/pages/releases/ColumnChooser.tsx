import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { isVisible, toggleColumn, type ColumnChoice, type ColumnGroup, type GridColumn } from "./columns";

const GROUPS: ColumnGroup[] = ["release", "paper", "numbers", "custom", "colleagues"];

/** Which columns to show. The choice is saved per person (R7.5.2). */
export default function ColumnChooser({
  columns,
  choice,
  onChange,
}: {
  columns: GridColumn[];
  choice: ColumnChoice;
  onChange: (choice: ColumnChoice) => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: PointerEvent): void => {
      if (!box.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);

  return (
    <div
      ref={box}
      className="relative"
      onKeyDown={(event) => {
        if (event.key === "Escape") setOpen(false);
      }}
    >
      <button
        type="button"
        className="btn-small"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        {t("data.columns")}
      </button>
      {open && (
        <div className="column-chooser">
          {GROUPS.map((group) => {
            const members = columns.filter((column) => column.group === group);
            if (members.length === 0) return null;
            return (
              <fieldset key={group} className="mb-3xs">
                <legend className="field-label">{t(`data.column_groups.${group}`)}</legend>
                {members.map((column) => (
                  <label key={column.id} className="flex items-center gap-5xs py-5xs">
                    <input
                      type="checkbox"
                      disabled={column.locked}
                      checked={isVisible(column, choice)}
                      onChange={(event) =>
                        onChange(toggleColumn(column, choice, event.target.checked))
                      }
                    />
                    {column.label}
                  </label>
                ))}
              </fieldset>
            );
          })}
        </div>
      )}
    </div>
  );
}

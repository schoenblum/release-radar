import { useEffect, useRef, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

/**
 * Opens beside a table, not inside it: a wide table scrolls sideways, which would carry a
 * panel in one of its rows out of view. What is behind it stays visible and usable.
 */
export default function SidePanel({
  title,
  onClose,
  children,
  closeLabel,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  closeLabel?: string;
}) {
  const { t } = useTranslation();
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!panel.current?.contains(document.activeElement)) panel.current?.focus();
  }, []);
  return (
    <aside
      ref={panel}
      role="dialog"
      aria-label={title}
      tabIndex={-1}
      className="side-panel"
      onKeyDown={(event) => {
        if (event.key === "Escape") onClose();
      }}
    >
      <div className="mb-3xs flex items-start justify-between gap-4xs">
        <h2 className="font-semibold">{title}</h2>
        <button type="button" className="btn-small" onClick={onClose}>
          {closeLabel ?? t("common.cancel")}
        </button>
      </div>
      {children}
    </aside>
  );
}

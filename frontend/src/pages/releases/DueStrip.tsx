import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, http } from "../../api/client";
import { errorMessage } from "../../api/errors";
import type { DueItem, Reading, ReleaseSaved } from "../../api/types";
import { normaliseDate } from "../../dates";
import { DUE_KEY, useReleaseActions } from "./useReleaseData";

function itemKey(item: DueItem): string {
  return item.kind === "reading"
    ? `reading-${item.reading_id}`
    : `custom-${item.release_id}-${item.field_key}`;
}

type Body = { value: unknown } | { state: "not_applicable" };

function without<T>(record: Record<string, T>, key: string): Record<string, T> {
  const copy = { ...record };
  delete copy[key];
  return copy;
}

/**
 * What is due, plainly (R7.5.1): today or earlier, and the next few days. Type a number, press
 * Enter, and the next one is ready. Nothing here is late, and nothing is red (P5).
 */
export default function DueStrip({ onOpen }: { onOpen: (releaseId: string) => void }) {
  const { t, i18n } = useTranslation();
  const actions = useReleaseActions();
  const { data: items } = useQuery({
    queryKey: DUE_KEY,
    queryFn: () => http.get<DueItem[]>("/releases/due"),
    refetchInterval: 60_000,
  });
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState<ReadonlySet<string>>(new Set());
  const inputs = useRef(new Map<string, HTMLInputElement>());
  const [focusKey, setFocusKey] = useState<string | null>(null);

  useEffect(() => {
    if (focusKey) inputs.current.get(focusKey)?.focus();
  }, [focusKey, items]);

  async function send(item: DueItem, body: Body): Promise<void> {
    const key = itemKey(item);
    setSaving((current) => new Set(current).add(key));
    setErrors((current) => without(current, key));
    try {
      if (item.kind === "reading") {
        const saved = await http.patch<Reading>(`/readings/${item.reading_id}`, {
          ...body,
          version: item.version,
        });
        actions.storeReading(item.release_id, saved);
      } else {
        const saved = await http.patch<ReleaseSaved>(
          `/releases/${item.release_id}/custom/${encodeURIComponent(item.field_key ?? "")}`,
          { ...body, version: item.version },
        );
        actions.storeRelease(saved.release);
      }
      setDrafts((current) => without(current, key));
      actions.refreshDue();
    } catch (failure) {
      // Someone else has dealt with it, so a fresh list is all that is needed.
      if (failure instanceof ApiError && failure.code === "conflict") actions.refreshDue();
      else setErrors((current) => ({ ...current, [key]: failure }));
    } finally {
      setSaving((current) => {
        const next = new Set(current);
        next.delete(key);
        return next;
      });
    }
  }

  function nextKey(item: DueItem, list: DueItem[]): string | null {
    const at = list.findIndex((entry) => itemKey(entry) === itemKey(item));
    const next = list[at + 1] ?? null;
    return next ? itemKey(next) : null;
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>, item: DueItem, list: DueItem[]): void {
    if (event.nativeEvent.isComposing) return;
    if (event.key !== "Enter") return;
    event.preventDefault();
    const typed = (drafts[itemKey(item)] ?? "").trim();
    const value = item.field_type === "date" ? normaliseDate(typed) : typed;
    if (value) void send(item, { value });
    setFocusKey(nextKey(item, list));
  }

  if (!items) return null;

  const label = (item: DueItem): string =>
    (i18n.language === "ja" && item.label_ja) || item.label_en;

  if (items.length === 0) {
    return <p className="due-strip due-caught-up">{t("data.caught_up")}</p>;
  }

  return (
    <section className="due-strip" aria-label={t("data.due_title")}>
      <h2 className="mb-5xs text-sm font-semibold">
        {t("data.due_count", { count: items.length })}
      </h2>
      <ul className="due-list">
        {items.map((item) => {
          const key = itemKey(item);
          const isDate = item.field_type === "date";
          const hasOwnEditor =
            item.kind === "custom" &&
            !["integer", "number", "text", "url", "date"].includes(item.field_type ?? "");
          return (
            <li key={key} className="due-item">
              <button type="button" className="due-title" onClick={() => onOpen(item.release_id)}>
                {item.release_code ? `${item.release_code} · ` : ""}
                {item.release_title ?? t("data.no_title")}
              </button>
              <span className="due-measure">{label(item)}</span>
              <span className={item.due_now ? "due-date" : "due-date due-soon"}>
                {t(item.due_now ? "data.due_on" : "data.coming_up", { date: item.due_date })}
              </span>
              <span className="due-controls">
                {hasOwnEditor ? (
                  <button
                    type="button"
                    className="btn-small"
                    onClick={() => onOpen(item.release_id)}
                  >
                    {t("data.open_to_fill")}
                  </button>
                ) : (
                  <input
                    ref={(element) => {
                      if (element) inputs.current.set(key, element);
                      else inputs.current.delete(key);
                    }}
                    className="due-input"
                    aria-label={`${label(item)}: ${item.release_title ?? ""}`}
                    inputMode={
                      item.kind === "reading" || item.field_type === "integer" ? "decimal" : undefined
                    }
                    placeholder={isDate ? "YYYY-MM-DD" : undefined}
                    value={drafts[key] ?? ""}
                    onChange={(event) =>
                      setDrafts((current) => ({ ...current, [key]: event.target.value }))
                    }
                    onKeyDown={(event) => onKeyDown(event, item, items)}
                  />
                )}
                <button
                  type="button"
                  className="btn-small"
                  disabled={saving.has(key)}
                  onClick={() => void send(item, { state: "not_applicable" })}
                >
                  {t("data.not_applicable")}
                </button>
              </span>
              {errors[key] !== undefined && (
                <p role="alert" className="field-error due-error">
                  {errorMessage(t, errors[key])}
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

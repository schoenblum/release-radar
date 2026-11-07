import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState, type KeyboardEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { http } from "../../api/client";
import { errorMessage } from "../../api/errors";
import type { Author, Researcher, ResearcherPage, Unit } from "../../api/types";
import RecordSummary from "../../components/RecordSummary";

function authorName(author: Author): string {
  return author.name ?? [author.given, author.family].filter(Boolean).join(" ");
}

type Choice =
  | { kind: "author"; author: Author; name: string }
  | { kind: "record"; record: Researcher }
  | { kind: "create"; name: string }
  | { kind: "clear" };

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

/**
 * Chooses the corresponding researcher (R7.5.4): the paper's authors first, then the directory,
 * then a new record. A name alone never decides which record is meant (R6.3.1), so choosing an
 * author with a namesake in the directory shows the records to choose from.
 */
export default function ResearcherPicker({
  authors,
  units,
  hasValue,
  autoFocus = false,
  onPick,
  onClear,
  onCancel,
  onLeave,
}: {
  authors: Author[];
  units: Unit[];
  hasValue: boolean;
  autoFocus?: boolean;
  onPick: (record: { id: string; name: string }) => void;
  onClear?: () => void;
  onCancel: () => void;
  /** Tab: leave without choosing, in a direction. */
  onLeave?: (backwards: boolean) => void;
}) {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const term = useDebounced(query.trim(), 200);

  const { data } = useQuery({
    queryKey: ["researchers", "picker", term],
    queryFn: () =>
      http.get<ResearcherPage>(`/researchers?limit=8&search=${encodeURIComponent(term)}`),
    enabled: term.length > 0,
  });

  const choices = useMemo<Choice[]>(() => {
    const records = term.length > 0 ? (data?.items ?? []) : [];
    const lowered = query.trim().toLowerCase();
    const named = authors
      .map((author) => ({ kind: "author" as const, author, name: authorName(author) }))
      .filter((choice) => choice.name && choice.name.toLowerCase().includes(lowered));
    const list: Choice[] = [...named, ...records.map((record) => ({ kind: "record" as const, record }))];
    if (query.trim()) list.push({ kind: "create", name: query.trim() });
    if (hasValue && onClear && !query.trim()) list.push({ kind: "clear" });
    return list;
  }, [authors, data, term, query, hasValue, onClear]);
  const active = Math.min(cursor, Math.max(choices.length - 1, 0));

  async function create(name: string, author?: Author): Promise<void> {
    const record = await http.post<Researcher>("/researchers", {
      name,
      given_name: author?.given ?? null,
      family_name: author?.family ?? null,
      orcid: author?.orcid ?? null,
      // From the paper's author list, so someone should have a look, as with the import.
      status: author ? "unverified" : "incomplete",
    });
    onPick({ id: record.id, name: record.name });
  }

  async function choose(choice: Choice): Promise<void> {
    setError(null);
    setBusy(true);
    try {
      if (choice.kind === "record") {
        onPick({ id: choice.record.id, name: choice.record.name });
      } else if (choice.kind === "clear") {
        onClear?.();
      } else if (choice.kind === "create") {
        await create(choice.name);
      } else {
        const found = await http.get<ResearcherPage>(
          `/researchers?limit=8&search=${encodeURIComponent(choice.name)}`,
        );
        const same = found.items.filter(
          (record) => record.name.trim().toLowerCase() === choice.name.toLowerCase(),
        );
        if (same.length > 0) {
          // Someone of this name exists. Whether it is the same person is for a person to say.
          setQuery(choice.name);
          setCursor(0);
        } else {
          await create(choice.name, choice.author);
        }
      }
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>): void {
    if (event.nativeEvent.isComposing) return;
    event.stopPropagation();
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setCursor(Math.min(active + 1, choices.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setCursor(Math.max(active - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      const choice = choices[active];
      if (choice) void choose(choice);
    } else if (event.key === "Escape") {
      event.preventDefault();
      onCancel();
    } else if (event.key === "Tab" && onLeave) {
      event.preventDefault();
      onLeave(event.shiftKey);
    }
  }

  function label(choice: Choice): ReactNode {
    if (choice.kind === "author") return choice.name;
    if (choice.kind === "record") return <RecordSummary record={choice.record} units={units} />;
    if (choice.kind === "clear") return t("data.researcher_clear");
    return t("data.researcher_create", { name: choice.name });
  }

  function heading(index: number): string | null {
    const current = choices[index];
    const previous = choices[index - 1];
    if (current.kind === previous?.kind) return null;
    if (current.kind === "author") return t("data.researcher_authors");
    if (current.kind === "record") return t("data.researcher_directory");
    return null;
  }

  return (
    <div className="picker">
      <input
        ref={(element) => {
          if (element && autoFocus && document.activeElement !== element) element.focus();
        }}
        className="picker-input"
        role="combobox"
        aria-expanded={choices.length > 0}
        aria-label={t("data.researcher_search")}
        placeholder={t("data.researcher_search")}
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setCursor(0);
        }}
        onKeyDown={onKeyDown}
        onBlur={onCancel}
      />
      {(choices.length > 0 || error !== null) && (
        <div className="picker-list">
          {error !== null && (
            <p role="alert" className="field-error">
              {errorMessage(t, error)}
            </p>
          )}
          <ul role="listbox" aria-label={t("data.researcher_search")}>
            {choices.map((choice, index) => {
              const title = heading(index);
              return (
                <li key={`${choice.kind}-${index}`} role="presentation">
                  {title && <p className="picker-heading">{title}</p>}
                  <button
                    type="button"
                    role="option"
                    aria-selected={index === active}
                    tabIndex={-1}
                    disabled={busy}
                    className={index === active ? "picker-option is-active" : "picker-option"}
                    // Before the input loses focus, which would close a grid editor.
                    onMouseDown={(event) => {
                      event.preventDefault();
                      void choose(choice);
                    }}
                  >
                    {label(choice)}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

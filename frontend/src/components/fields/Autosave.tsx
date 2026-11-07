import { useEffect, useState, type KeyboardEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../api/client";
import { errorMessage } from "../../api/errors";

/**
 * Fields that save themselves, one at a time, with no Save button. The step 1.5 grid
 * uses the same rules:
 * - Enter or leaving the field saves. Esc goes back.
 * - Invalid input stays on screen with a plain explanation, and blocks nothing else.
 * - If someone else changed the same field meanwhile, the person sees the current value
 *   and chooses which to keep (R3.3.3).
 */

type Status =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "saved" }
  | { kind: "error"; error: unknown }
  | { kind: "conflict"; value: unknown; version: number };

export type Save<T> = (value: T, version: number) => Promise<unknown>;

const SAVED_MESSAGE_MS = 1500;

interface SavedResponse {
  value?: unknown;
  version?: number;
}

function useAutosave<T extends string | boolean>(
  value: T,
  version: number,
  save: Save<T>,
  fromServer: (value: unknown) => T,
) {
  const [draft, setDraft] = useState<T>(value);
  const [previous, setPrevious] = useState<T>(value);
  const [savedVersion, setSavedVersion] = useState(version);
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  // A value that arrives from a refetch replaces the draft, unless the person has been
  // typing: what is being typed is never overwritten.
  if (value !== previous) {
    setPrevious(value);
    if (draft === previous) setDraft(value);
  }

  const currentVersion = Math.max(version, savedVersion);

  useEffect(() => {
    if (status.kind !== "saved") return;
    const timer = setTimeout(() => setStatus({ kind: "idle" }), SAVED_MESSAGE_MS);
    return () => clearTimeout(timer);
  }, [status.kind]);

  async function commit(next: T, atVersion: number = currentVersion): Promise<void> {
    const retrying = status.kind === "conflict" || status.kind === "error";
    if (next === value && !retrying) return;
    setStatus({ kind: "saving" });
    try {
      const result = (await save(next, atVersion)) as SavedResponse | undefined;
      if (typeof result?.version === "number") setSavedVersion(result.version);
      // The server may have tidied the value, for example by trimming spaces.
      if (result && "value" in result) setDraft(fromServer(result.value));
      setStatus({ kind: "saved" });
    } catch (error) {
      if (error instanceof ApiError && error.code === "conflict") {
        setStatus({
          kind: "conflict",
          value: error.body.current_value,
          version: Number(error.body.current_version),
        });
      } else {
        setStatus({ kind: "error", error });
      }
    }
  }

  function revert(): void {
    setDraft(value);
    setStatus({ kind: "idle" });
  }

  function keepMine(): void {
    if (status.kind === "conflict") void commit(draft, status.version);
  }

  function useTheirs(): void {
    if (status.kind !== "conflict") return;
    setDraft(fromServer(status.value));
    setSavedVersion(status.version);
    setStatus({ kind: "idle" });
  }

  return { draft, setDraft, status, commit, revert, keepMine, useTheirs };
}

function StatusLine({
  status,
  keepMine,
  useTheirs,
}: {
  status: Status;
  keepMine: () => void;
  useTheirs: () => void;
}) {
  const { t } = useTranslation();
  if (status.kind === "saving") {
    return (
      <p role="status" className="field-status">
        {t("common.saving")}
      </p>
    );
  }
  if (status.kind === "saved") {
    return (
      <p role="status" className="field-status">
        {t("common.saved")}
      </p>
    );
  }
  if (status.kind === "error") {
    return (
      <p role="alert" className="field-error">
        {errorMessage(t, status.error)}
      </p>
    );
  }
  if (status.kind === "conflict") {
    const shown =
      status.value === null || status.value === "" ? t("conflict.empty") : String(status.value);
    return (
      <div role="alert" className="field-error">
        <p>{t("conflict.message", { value: shown })}</p>
        <div className="mt-5xs flex gap-5xs">
          <button type="button" className="btn-small" onClick={keepMine}>
            {t("conflict.keep_mine")}
          </button>
          <button type="button" className="btn-small" onClick={useTheirs}>
            {t("conflict.use_theirs")}
          </button>
        </div>
      </div>
    );
  }
  return null;
}

const textFromServer = (value: unknown): string => (value == null ? "" : String(value));

interface TextFieldProps {
  id?: string;
  label: string;
  value: string | number | null | undefined;
  version?: number;
  save: Save<string>;
  type?: "text" | "number" | "date" | "email";
  multiline?: boolean;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  hint?: string;
  title?: string;
}

export function TextField({
  id,
  label,
  value,
  version = 0,
  save,
  type = "text",
  multiline = false,
  placeholder,
  className = "cell-input",
  disabled = false,
  hint,
  title,
}: TextFieldProps) {
  const { draft, setDraft, status, commit, revert, keepMine, useTheirs } = useAutosave<string>(
    textFromServer(value),
    version,
    save,
    textFromServer,
  );

  function onKeyDown(event: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>): void {
    if (event.key === "Escape") {
      revert();
    } else if (event.key === "Enter" && !multiline) {
      event.preventDefault();
      if (status.kind === "conflict") keepMine();
      else void commit(draft);
    }
  }

  const shared = {
    id,
    "aria-label": id ? undefined : label,
    "aria-invalid": status.kind === "error" || undefined,
    className,
    disabled,
    placeholder,
    title,
    value: draft,
    onKeyDown,
    onBlur: () => {
      // During a conflict the choice is the person's: clicking one of the two buttons
      // leaves this field, and that must not save anything by itself.
      if (status.kind !== "conflict") void commit(draft);
    },
  };

  return (
    <div>
      {multiline ? (
        <textarea
          {...shared}
          rows={2}
          onChange={(event) => setDraft(event.target.value)}
        />
      ) : (
        <input
          {...shared}
          type={type}
          onChange={(event) => setDraft(event.target.value)}
        />
      )}
      {hint && <p className="field-hint">{hint}</p>}
      <StatusLine status={status} keepMine={keepMine} useTheirs={useTheirs} />
    </div>
  );
}

export interface Option {
  value: string;
  label: string;
}

interface SelectFieldProps {
  id?: string;
  label: string;
  value: string | null | undefined;
  version?: number;
  save: Save<string>;
  options: Option[];
  /** Offer an empty choice, with this label. */
  emptyLabel?: string;
  className?: string;
  disabled?: boolean;
  hint?: string;
}

export function SelectField({
  id,
  label,
  value,
  version = 0,
  save,
  options,
  emptyLabel,
  className = "cell-input",
  disabled = false,
  hint,
}: SelectFieldProps) {
  const { draft, setDraft, status, commit, keepMine, useTheirs } = useAutosave<string>(
    textFromServer(value),
    version,
    save,
    textFromServer,
  );
  return (
    <div>
      <select
        id={id}
        aria-label={id ? undefined : label}
        className={className}
        disabled={disabled}
        value={draft}
        onChange={(event) => {
          setDraft(event.target.value);
          void commit(event.target.value);
        }}
      >
        {emptyLabel !== undefined && <option value="">{emptyLabel}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {hint && <p className="field-hint">{hint}</p>}
      <StatusLine status={status} keepMine={keepMine} useTheirs={useTheirs} />
    </div>
  );
}

interface ToggleFieldProps {
  label: string;
  value: boolean;
  version?: number;
  save: Save<boolean>;
  disabled?: boolean;
  title?: string;
  children?: ReactNode;
}

export function ToggleField({
  label,
  value,
  version = 0,
  save,
  disabled = false,
  title,
  children,
}: ToggleFieldProps) {
  const { draft, setDraft, status, commit, keepMine, useTheirs } = useAutosave<boolean>(
    value,
    version,
    save,
    Boolean,
  );
  return (
    <div>
      <label className="inline-flex items-center gap-5xs" title={title}>
        <input
          type="checkbox"
          aria-label={children ? undefined : label}
          disabled={disabled}
          checked={draft}
          onChange={(event) => {
            setDraft(event.target.checked);
            void commit(event.target.checked);
          }}
        />
        {children}
      </label>
      <StatusLine status={status} keepMine={keepMine} useTheirs={useTheirs} />
    </div>
  );
}

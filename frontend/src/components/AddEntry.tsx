import { useState, type FormEvent } from "react";

import { useTranslation } from "react-i18next";

import { errorMessage } from "../api/errors";

/** One box to add an entry: type a name, press Enter, and the rest can follow in the table. */
export default function AddEntry({
  label,
  onAdd,
}: {
  label: string;
  onAdd: (name: string) => Promise<unknown>;
}) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [error, setError] = useState<unknown>(null);

  async function submit(event: FormEvent): Promise<void> {
    event.preventDefault();
    if (!name.trim()) return;
    setError(null);
    try {
      await onAdd(name);
      setName("");
    } catch (failure) {
      setError(failure);
    }
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="mt-3xs max-w-md">
      <div className="flex gap-4xs">
        <input
          className="input"
          aria-label={label}
          placeholder={label}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <button type="submit" className="btn-quiet">
          {t("common.add")}
        </button>
      </div>
      {error !== null && (
        <p role="alert" className="field-error">
          {errorMessage(t, error)}
        </p>
      )}
    </form>
  );
}

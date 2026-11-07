import { useState, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "../../api/errors";
import type { CrossrefStatus, ReleaseCreated } from "../../api/types";
import { useToast } from "../../components/Toast";
import { looksLikeDoi } from "./parse";

/**
 * The quickest way to start a release (R7.5.4): paste a DOI or type a title, press Enter, and
 * carry on with the next one. Everything else can follow.
 */
export default function NewReleaseRow({
  create,
  onLeaveDown,
}: {
  create: (payload: { title?: string; doi?: string }) => Promise<ReleaseCreated>;
  onLeaveDown: () => void;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  function announce(status: CrossrefStatus | null, created: ReleaseCreated): void {
    if (status === "found") {
      toast({ text: t("data.crossref_found", { title: created.paper_title ?? created.doi ?? "" }) });
    } else if (status) {
      toast({ text: t(`data.crossref_${status}`) });
    }
  }

  async function submit(): Promise<void> {
    const value = text.trim();
    if (!value || busy) return;
    setBusy(true);
    setError(null);
    try {
      const created = await create(looksLikeDoi(value) ? { doi: value } : { title: value });
      setText("");
      announce(created.crossref, created);
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>): void {
    if (event.nativeEvent.isComposing) return;
    event.stopPropagation();
    if (event.key === "Enter") {
      event.preventDefault();
      void submit();
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      onLeaveDown();
    } else if (event.key === "Escape") {
      setText("");
      setError(null);
    }
  }

  return (
    <div className="grid-new-box">
      <input
        className="grid-new-input"
        aria-label={t("data.new_release")}
        placeholder={t("data.new_release")}
        value={text}
        // Not disabled: that would lose the focus, and the next release is typed right here.
        readOnly={busy}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={onKeyDown}
      />
      {busy && <span className="field-status">{t("common.saving")}</span>}
      {error !== null && (
        <span role="alert" className="field-error">
          {errorMessage(t, error)}
        </span>
      )}
    </div>
  );
}

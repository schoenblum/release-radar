import { Component, type ErrorInfo, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

/**
 * A page that loads separately (Analysis) can fail to arrive: after an update its old file is
 * gone, or the connection drops. Without a boundary React would unmount the whole app, leaving
 * a blank page on which even Back does nothing. With it, the header stays, the page says what
 * happened, and moving to another page (Layout keys this by address) starts afresh.
 */
function isLoadFailure(error: unknown): boolean {
  const text = error instanceof Error ? `${error.name} ${error.message}` : String(error);
  return /dynamically imported module|Importing a module script failed|ChunkLoadError|Loading chunk|error loading dynamically/i.test(
    text,
  );
}

function Fallback({ loadFailure }: { loadFailure: boolean }) {
  const { t } = useTranslation();
  return (
    <div role="alert" className="max-w-2xl">
      <h1 className="mb-4xs text-3xl">{t("page_error.title")}</h1>
      <p className="mb-3xs text-content-secondary">
        {loadFailure ? t("page_error.load_failed") : t("page_error.failed")}
      </p>
      <button type="button" className="btn-primary" onClick={() => window.location.reload()}>
        {t("page_error.reload")}
      </button>
    </div>
  );
}

export default class PageErrorBoundary extends Component<
  { children: ReactNode },
  { error: unknown }
> {
  override state: { error: unknown } = { error: null };

  static getDerivedStateFromError(error: unknown): { error: unknown } {
    return { error };
  }

  override componentDidCatch(error: unknown, info: ErrorInfo): void {
    // Left in the console for whoever looks into it; the page itself stays plain.
    console.error("A page failed to render", error, info.componentStack);
  }

  override render(): ReactNode {
    if (this.state.error === null) return this.props.children;
    return <Fallback loadFailure={isLoadFailure(this.state.error)} />;
  }
}

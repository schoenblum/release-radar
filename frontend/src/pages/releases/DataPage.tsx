import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { api } from "../../api/client";
import type { CrossrefStatus, Release, UserPreferences } from "../../api/types";
import { useAuth } from "../../auth";
import { PageLoading } from "../../components/Spinner";
import { useToast } from "../../components/Toast";
import ColumnChooser from "./ColumnChooser";
import type { ColumnChoice, Commit } from "./columns";
import DueStrip from "./DueStrip";
import NewReleaseRow from "./NewReleaseRow";
import ReleaseDrawer from "./ReleaseDrawer";
import ReleaseGrid from "./ReleaseGrid";
import { useCellSaves } from "./useCellSaves";
import { useGridColumns } from "./useGridContext";
import { useReleaseActions, useReleaseList, type DataView } from "./useReleaseData";

const NO_CHOICE: ColumnChoice = { hidden: [], shown: [] };

/**
 * Keeps rows where they are while someone works: changing a date must not make the row jump
 * away. A new release goes on top, and the order is fresh when the view changes or the page
 * loads.
 */
function useSteadyOrder(view: DataView, releases: Release[] | undefined): Release[] {
  const [order, setOrder] = useState<{ view: DataView; ids: string[] }>({ view, ids: [] });
  const list = useMemo(() => releases ?? [], [releases]);
  const incoming = new Set(list.map((release) => release.id));
  const sameView = order.view === view;
  const known = new Set(sameView ? order.ids : []);
  const differs =
    !sameView ||
    list.some((release) => !known.has(release.id)) ||
    order.ids.some((id) => !incoming.has(id));
  if (differs && releases) {
    const kept = sameView ? order.ids.filter((id) => incoming.has(id)) : [];
    const keptSet = new Set(kept);
    const fresh = list.filter((release) => !keptSet.has(release.id)).map((release) => release.id);
    setOrder({ view, ids: [...fresh, ...kept] });
  }
  return useMemo(() => {
    const byId = new Map(list.map((release) => [release.id, release]));
    return order.ids.flatMap((id) => {
      const release = byId.get(id);
      return release ? [release] : [];
    });
  }, [list, order.ids]);
}

/** The home page for most visits (D10, D30): what is due, the grid, and a drawer per release. */
export default function DataPage() {
  const { t } = useTranslation();
  const { user, setUser } = useAuth();
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const requested = params.get("view");
  const view: DataView = requested === "mine" || requested === "all" ? requested : (user?.landing ?? "all");
  const openId = params.get("release");

  const { data: page, isLoading } = useReleaseList(view);
  const { columns, context } = useGridColumns();
  const actions = useReleaseActions();
  const rows = useSteadyOrder(view, page?.items);

  const [choice, setChoice] = useState<ColumnChoice>(
    () => user?.preferences?.data_columns ?? NO_CHOICE,
  );

  const notifyPaper = useCallback(
    (status: CrossrefStatus) => {
      if (status !== "found") toast({ text: t(`data.crossref_${status}`) });
    },
    [t, toast],
  );

  const apply = useCallback(
    async (releaseId: string, commit: Commit, version?: number) => {
      await actions.save(releaseId, commit, version);
      // A new DOI fills in what is still empty. Trouble here says so, and nothing is lost.
      if (commit.kind === "field" && commit.field === "doi" && commit.value) {
        void actions
          .fetchPaper(releaseId, false)
          .then(notifyPaper)
          .catch(() => notifyPaper("unavailable"));
      }
    },
    [actions, notifyPaper],
  );
  const saves = useCellSaves(apply);

  function chooseColumns(next: ColumnChoice): void {
    setChoice(next);
    const preferences: UserPreferences = { data_columns: next };
    void api
      .updateMe({ preferences })
      .then((updated) => setUser(updated))
      .catch(() => toast({ text: t("data.columns_not_saved") }));
  }

  function setParam(name: string, value: string | null): void {
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        if (value === null) next.delete(name);
        else next.set(name, value);
        return next;
      },
      { replace: name === "release" },
    );
  }

  const openRelease = useCallback(
    (releaseId: string) => {
      setParams(
        (current) => {
          const next = new URLSearchParams(current);
          next.set("release", releaseId);
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  if (!user) return null;
  if (isLoading || !columns || !context) return <PageLoading />;

  const canEdit = context.canEdit;
  const opened = openId ? rows.find((release) => release.id === openId) : undefined;
  const focusGrid = (): void => {
    document.querySelector<HTMLElement>("[role=grid]")?.focus();
  };

  return (
    <div>
      <div className="mb-3xs flex flex-wrap items-center justify-between gap-4xs">
        <h1 className="text-3xl">{t("nav.data")}</h1>
        <div className="flex flex-wrap items-center gap-4xs">
          <div role="group" aria-label={t("data.view_label")} className="view-toggle">
            {(["mine", "all"] as const).map((item) => (
              <button
                key={item}
                type="button"
                aria-pressed={view === item}
                className={view === item ? "view-toggle-on" : "view-toggle-off"}
                onClick={() => setParam("view", item)}
              >
                {t(`data.views.${item}`)}
              </button>
            ))}
          </div>
          <ColumnChooser columns={columns} choice={choice} onChange={chooseColumns} />
        </div>
      </div>

      {view === "mine" && canEdit && (
        <DueStrip onOpen={openRelease} />
      )}

      <ReleaseGrid
        rows={rows}
        allColumns={columns}
        choice={choice}
        canEdit={canEdit}
        saves={saves}
        units={context.units}
        onOpen={openRelease}
        onRefresh={actions.refreshList}
        empty={
          view === "mine" && page && !page.has_writer_entry
            ? t("data.empty_no_writer")
            : t(canEdit ? "data.empty" : "data.empty_read_only")
        }
        newRow={
          canEdit ? <NewReleaseRow create={actions.create} onLeaveDown={focusGrid} /> : null
        }
      />
      <p className="mt-4xs text-sm text-content-secondary">
        {t("data.count", { count: rows.length, total: page?.total ?? rows.length })}
        {canEdit ? ` · ${t("data.keys_hint")}` : ""}
      </p>

      {opened && (
        <ReleaseDrawer
          key={opened.id}
          release={opened}
          context={context}
          onClose={() => setParam("release", null)}
        />
      )}
    </div>
  );
}

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { api } from "../../api/client";
import type { CrossrefStatus, ReleaseFilters, UserPreferences } from "../../api/types";
import { useAuth } from "../../auth";
import { PageLoading } from "../../components/Spinner";
import { useToast } from "../../components/Toast";
import ColumnChooser from "./ColumnChooser";
import type { ColumnChoice, Commit } from "./columns";
import DueStrip from "./DueStrip";
import ExportMenu from "./ExportMenu";
import FilterBar from "./FilterBar";
import NewReleaseRow from "./NewReleaseRow";
import ReleaseDrawer from "./ReleaseDrawer";
import ReleaseGrid from "./ReleaseGrid";
import { useCellSaves } from "./useCellSaves";
import { useGridColumns } from "./useGridContext";
import {
  useCreatedReleases,
  useReleaseActions,
  useReleaseList,
  type DataView,
} from "./useReleaseData";
import { useSteadyOrder } from "./useSteadyOrder";
import {
  compareBy,
  filterQuery,
  filtersFrom,
  hasFilters,
  nextSort,
  SORT_PARAM,
  sortFrom,
  sortText,
  withFilter,
  withoutFilters,
} from "./viewState";

const NO_CHOICE: ColumnChoice = { hidden: [], shown: [] };

/** The home page for most visits (D10, D30): what is due, the grid, and a drawer per release. */
export default function DataPage() {
  const { t, i18n } = useTranslation();
  const { user, setUser } = useAuth();
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const requested = params.get("view");
  const view: DataView = requested === "mine" || requested === "all" ? requested : (user?.landing ?? "all");
  const openId = params.get("release");
  const filters = useMemo(() => filtersFrom(params), [params]);
  const sort = useMemo(() => sortFrom(params), [params]);

  const { data: page, isLoading, isPlaceholderData } = useReleaseList(view, filters);
  const { columns, context } = useGridColumns();
  const actions = useReleaseActions();

  const sortColumn = sort ? columns?.find((column) => column.id === sort.column) : undefined;
  const compare = useMemo(
    () => (sort && sortColumn ? compareBy(sortColumn, sort.desc, i18n.language) : null),
    [sort, sortColumn, i18n.language],
  );
  const orderKey = [view, filterQuery(filters), sortText(sort), compare ? "sorted" : ""].join("|");
  const created = useCreatedReleases();
  const forgetCreated = actions.forgetCreated;
  useEffect(() => {
    forgetCreated();
  }, [orderKey, forgetCreated]);
  const items = useMemo(() => {
    if (!page) return undefined;
    const listed = new Set(page.items.map((release) => release.id));
    return [...created.filter((release) => !listed.has(release.id)), ...page.items];
  }, [page, created]);
  const rows = useSteadyOrder(orderKey, items, !isPlaceholderData, compare);

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

  function setFilter(key: keyof ReleaseFilters, value: string | number | null): void {
    // Typing a search replaces the address as it goes, rather than adding a step per pause.
    setParams((current) => withFilter(current, key, value), { replace: key === "q" });
  }

  const onSort = useCallback(
    (columnId: string) => {
      setParams((current) => {
        const next = new URLSearchParams(current);
        const chosen = sortText(nextSort(sortFrom(current), columnId));
        if (chosen) next.set(SORT_PARAM, chosen);
        else next.delete(SORT_PARAM);
        return next;
      });
    },
    [setParams],
  );

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
  const narrowed = hasFilters(filters);
  const opened = openId ? rows.find((release) => release.id === openId) : undefined;
  const focusGrid = (): void => {
    document.querySelector<HTMLElement>("[role=grid]")?.focus();
  };
  const empty = narrowed
    ? t("data.empty_filtered")
    : view === "mine" && page && !page.has_writer_entry
      ? t("data.empty_no_writer")
      : t(canEdit ? "data.empty" : "data.empty_read_only");

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
          <ExportMenu
            view={view}
            filters={filters}
            order={rows.map((release) => release.id)}
            shown={page?.total ?? rows.length}
          />
        </div>
      </div>

      {view === "mine" && canEdit && <DueStrip onOpen={openRelease} />}

      <FilterBar
        filters={filters}
        years={page?.academic_years ?? []}
        showWriter={view === "all"}
        context={context}
        onChange={setFilter}
        onClear={() => setParams((current) => withoutFilters(current))}
      />

      <ReleaseGrid
        rows={rows}
        allColumns={columns}
        choice={choice}
        canEdit={canEdit}
        saves={saves}
        units={context.units}
        sort={sort}
        onSort={onSort}
        onOpen={openRelease}
        onRefresh={actions.refreshList}
        empty={empty}
        newRow={
          canEdit ? <NewReleaseRow create={actions.create} onLeaveDown={focusGrid} /> : null
        }
      />
      <p className="mt-4xs text-sm text-content-secondary" aria-live="polite">
        {narrowed
          ? t("data.count_filtered", { count: page?.total ?? 0, total: page?.view_total ?? 0 })
          : t("data.count", { count: rows.length, total: page?.total ?? rows.length })}
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

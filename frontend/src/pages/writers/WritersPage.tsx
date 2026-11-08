import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { http } from "../../api/client";
import type { WriterMonthly, WriterMonthRow } from "../../api/types";
import ErrorNotice from "../../components/ErrorNotice";
import ExportPopover, { type ExportChoice } from "../../components/ExportPopover";
import { PageLoading } from "../../components/Spinner";
import { academicYearLabel } from "../../dates";

const YEAR_PARAM = "ay";

function monthDate(month: string): Date {
  const [year, number] = month.split("-").map(Number);
  return new Date(year, number - 1, 1);
}

function yearFrom(params: URLSearchParams): number | null {
  const text = params.get(YEAR_PARAM);
  return text && /^\d{4}$/.test(text) ? Number(text) : null;
}

/**
 * Releases per writer and month (R7.7.1), for everyone. Counts only: how a release does
 * depends mostly on its topic, not on who wrote it (R7.7.2).
 */
export default function WritersPage() {
  const { t, i18n } = useTranslation();
  const language = i18n.language === "ja" ? "ja" : "en";
  const [params, setParams] = useSearchParams();
  const asked = yearFrom(params);
  const { data, error, isLoading } = useQuery({
    queryKey: ["writers", "monthly", asked],
    queryFn: () =>
      http.get<WriterMonthly>(
        `/writers/monthly${asked === null ? "" : `?academic_year=${asked}`}`,
      ),
    placeholderData: keepPreviousData,
  });

  if (isLoading) return <PageLoading />;
  if (!data) return <ErrorNotice error={error} />;

  const year = data.academic_year;
  const short = new Intl.DateTimeFormat(language, { month: "short" });
  const long = new Intl.DateTimeFormat(language, { month: "long", year: "numeric" });
  const collator = new Intl.Collator(language, { numeric: true, sensitivity: "base" });
  const nameOf = (row: WriterMonthRow): string =>
    (language === "ja" && row.name_ja) || row.name_en || t("writers.no_writer");
  const rows = [...data.rows].sort(
    (a, b) =>
      Number(a.writer_id === null) - Number(b.writer_id === null) ||
      collator.compare(nameOf(a), nameOf(b)),
  );
  const dataLink = (writerId: string | null): string => {
    const query = new URLSearchParams({ view: "all", ay: String(year) });
    if (writerId) query.set("writer", writerId);
    return `/data?${query.toString()}`;
  };

  async function download({ format, language: chosen }: ExportChoice): Promise<void> {
    const query = new URLSearchParams({
      academic_year: String(year),
      format,
      language: chosen,
    });
    await http.download(
      `/writers/monthly/export?${query.toString()}`,
      `release_radar_writers_${year}.${format}`,
    );
  }

  return (
    <div>
      <div className="mb-3xs flex flex-wrap items-center justify-between gap-4xs">
        <h1 className="text-3xl">{t("nav.writers")}</h1>
        <div className="flex flex-wrap items-center gap-4xs">
          <label className="flex items-center gap-5xs text-sm">
            <span>{t("writers.year")}</span>
            <select
              className="filter-select"
              value={year}
              onChange={(event) => setParams({ [YEAR_PARAM]: event.target.value })}
            >
              {data.academic_years.map((option) => (
                <option key={option} value={option}>
                  {academicYearLabel(option, language)}
                </option>
              ))}
            </select>
          </label>
          <ExportPopover
            title={t("writers.export_title")}
            xlsxLabel={t("writers.export_xlsx")}
            notice={t("writers.export_notice")}
            download={download}
          />
        </div>
      </div>
      <p id="writers-caption" className="mb-3xs text-content-secondary">
        {t("writers.caption", { year: academicYearLabel(year, language) })}
      </p>
      <ErrorNotice error={error} />

      <div className="table-scroll">
        <table className="count-table" aria-describedby="writers-caption">
          <thead>
            <tr>
              <th scope="col">{t("writers.writer")}</th>
              {data.months.map((month) => (
                <th key={month} scope="col" title={long.format(monthDate(month))}>
                  {short.format(monthDate(month))}
                </th>
              ))}
              <th scope="col">{t("writers.total")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.writer_id ?? "none"}>
                <th
                  scope="row"
                  className={row.is_active ? undefined : "is-former"}
                  title={row.is_active ? undefined : t("writers.inactive")}
                >
                  {row.writer_id ? (
                    <Link to={dataLink(row.writer_id)}>{nameOf(row)}</Link>
                  ) : (
                    nameOf(row)
                  )}
                </th>
                {row.counts.map((count, place) => (
                  <td key={data.months[place]} className={count === 0 ? "is-zero" : undefined}>
                    {count}
                  </td>
                ))}
                <td className="count-total">{row.total}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row">
                <Link to={dataLink(null)}>{t("writers.total")}</Link>
              </th>
              {data.totals.map((count, place) => (
                <td key={data.months[place]}>{count}</td>
              ))}
              <td className="count-total">{data.total}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      {data.undated > 0 && (
        <p className="mt-4xs text-sm text-content-secondary">
          {t("writers.undated", { count: data.undated })}
        </p>
      )}
    </div>
  );
}

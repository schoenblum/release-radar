"""The Writers page (step 1.7, R7.7.1): releases per writer and month. Synthetic data."""

import csv
import io
from datetime import UTC, date, datetime

import openpyxl
import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Institution, Release, UserRole, Writer
from app.services.readings import today_in
from app.services.release_codes import academic_year
from app.services.writer_counts import months_of

URL = "/api/v1/writers/counts"


async def _institution() -> Institution:
    async with SessionLocal() as db:
        return await db.scalar(select(Institution).order_by(Institution.created_at))


async def _add(*rows):
    async with SessionLocal() as db:
        db.add_all(rows)
        await db.commit()
    return rows


def _release(institution_id, title, day, writer=None, **fields) -> Release:
    return Release(
        institution_id=institution_id,
        title=title,
        release_date=day,
        writer_id=writer.id if writer else None,
        **fields,
    )


@pytest.fixture
async def writers():
    """Two writers at work, one who left with releases this year, one who left before it."""
    institution_id = (await _institution()).id
    ada = Writer(
        institution_id=institution_id, display_name_en="Ada Writer", display_name_ja="エイダ"
    )
    bo = Writer(institution_id=institution_id, display_name_en="Bo Writer")
    gone = Writer(institution_id=institution_id, display_name_en="Cy Former", is_active=False)
    long_gone = Writer(institution_id=institution_id, display_name_en="Di Earlier", is_active=False)
    await _add(ada, bo, gone, long_gone)
    await _add(
        _release(institution_id, "April first", date(2025, 4, 1), ada),
        _release(institution_id, "April again", date(2025, 4, 30), ada),
        _release(institution_id, "Last of March", date(2026, 3, 31), ada),
        # The next academic year begins on 1 April.
        _release(institution_id, "Next year", date(2026, 4, 1), ada),
        _release(institution_id, "Before", date(2025, 3, 31), long_gone),
        _release(institution_id, "Autumn", date(2025, 10, 15), gone),
        _release(institution_id, "Nobody's", date(2025, 6, 2)),
        _release(institution_id, "No date yet", None, bo),
        _release(
            institution_id,
            "Removed",
            date(2025, 5, 5),
            bo,
            deleted_at=datetime(2025, 5, 6, tzinfo=UTC),
        ),
    )
    return {"ada": ada.id, "bo": bo.id, "gone": gone.id, "long_gone": long_gone.id}


async def _get(client, headers, **params):
    response = await client.get(URL, headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def _rows(body) -> dict[str, dict]:
    return {row["name_en"] or "(none)": row for row in body["rows"]}


def test_the_months_run_from_the_start_month_for_twelve_months():
    months = months_of(2025, 4)
    assert (months[0], months[-1]) == (date(2025, 4, 1), date(2026, 3, 1))
    assert months_of(2025, 1)[-1] == date(2025, 12, 1)
    assert months_of(2025, 10)[2] == date(2025, 12, 1)
    assert months_of(2025, 10)[3] == date(2026, 1, 1)


async def test_counts_each_writer_by_month_with_totals(client, admin_headers, writers):
    body = await _get(client, admin_headers, academic_year=2025)
    assert body["academic_year"] == 2025
    assert body["period"] == "month"
    assert body["columns"][0] == "2025-04" and body["columns"][-1] == "2026-03"
    rows = _rows(body)
    ada = rows["Ada Writer"]
    assert ada["counts"][0] == 2  # both April releases
    assert ada["counts"][11] == 1  # 31 March 2026 is still this year
    assert ada["total"] == 3
    assert ada["name_ja"] == "エイダ"
    # A writer at work with nothing this year still has a row, of zeros.
    assert rows["Bo Writer"]["counts"] == [0] * 12
    # Someone who left shows up for a year they wrote in, and not otherwise.
    assert rows["Cy Former"]["is_active"] is False
    assert rows["Cy Former"]["counts"][6] == 1
    assert "Di Earlier" not in rows
    # Releases without a writer are counted too, last.
    assert body["rows"][-1]["writer_id"] is None
    assert body["rows"][-1]["counts"][2] == 1
    assert body["totals"][0] == 2 and sum(body["totals"]) == body["total"] == 5
    # Not dated yet, so in no month; removed releases count nowhere.
    assert body["undated"] == 1


async def test_another_year_and_the_years_on_offer(client, admin_headers, writers):
    body = await _get(client, admin_headers, academic_year=2024)
    rows = _rows(body)
    assert rows["Di Earlier"]["counts"][11] == 1
    assert "Cy Former" not in rows
    current = academic_year(today_in((await _institution()).timezone), 4)
    assert body["academic_years"][0] == max(current, 2026)
    assert {2024, 2025, 2026, current} <= set(body["academic_years"])


async def test_the_current_year_is_the_default(client, admin_headers, writers):
    body = await _get(client, admin_headers)
    assert body["academic_year"] == academic_year(today_in((await _institution()).timezone), 4)


async def test_another_institution_counts_nowhere(client, admin_headers, writers):
    async with SessionLocal() as db:
        other = Institution(name_en="Elsewhere", timezone="UTC", settings={})
        db.add(other)
        await db.flush()
        stranger = Writer(institution_id=other.id, display_name_en="Stranger")
        db.add(stranger)
        await db.flush()
        db.add(_release(other.id, "Theirs", date(2025, 4, 2), stranger))
        await db.commit()
    body = await _get(client, admin_headers, academic_year=2025)
    assert "Stranger" not in _rows(body)
    assert body["totals"][0] == 2


async def test_everyone_signed_in_sees_it_and_nobody_else(client, headers_for, writers):
    assert (await client.get(URL)).status_code == 401
    viewer = await headers_for(UserRole.viewer)
    assert (await _get(client, viewer, academic_year=2025))["total"] == 5
    bad = await client.get(URL, headers=viewer, params={"academic_year": "soon"})
    assert bad.status_code == 422


async def test_the_export_holds_the_same_table(client, admin_headers, writers):
    response = await client.get(
        f"{URL}/export", headers=admin_headers, params={"academic_year": 2025}
    )
    assert response.status_code == 200, response.text
    assert 'filename="release_radar_writers_2025_' in response.headers["content-disposition"]
    workbook = openpyxl.load_workbook(io.BytesIO(response.content))
    assert workbook.sheetnames == ["Writers", "Read me"]
    rows = [[cell.value for cell in row] for row in workbook["Writers"].iter_rows()]
    assert rows[0][:2] == ["Writer", "2025-04"] and rows[0][-1] == "Total"
    names = [row[0] for row in rows[1:]]
    assert names == ["Ada Writer", "Bo Writer", "Cy Former", "No writer yet", "Total"]
    assert rows[1][1] == 2 and rows[1][-1] == 3
    assert rows[-1][1:] == [2, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 5]
    # The totals row is not part of what the filter sorts.
    assert workbook["Writers"].auto_filter.ref == "A1:N5"
    notes = "\n".join(str(row[0] or "") for row in workbook["Read me"].iter_rows(values_only=True))
    assert "Academic year 2025: 2025-04 to 2026-03." in notes
    assert "1 release(s) without a release date" in notes


async def test_the_export_in_japanese_as_csv(client, headers_for, writers):
    viewer = await headers_for(UserRole.viewer)
    response = await client.get(
        f"{URL}/export",
        headers=viewer,
        params={"academic_year": 2025, "format": "csv", "language": "ja"},
    )
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"\xef\xbb\xbf")
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert rows[0][0] == "ライター" and rows[0][-1] == "合計"
    # Sorted by the Japanese name where there is one.
    assert [row[0] for row in rows[1:]] == [
        "Bo Writer",
        "Cy Former",
        "エイダ",
        "ライター未設定",
        "合計",
    ]


async def test_all_years_count_by_academic_year(client, admin_headers, writers):
    body = await _get(client, admin_headers, all_years="true")
    assert body["period"] == "year" and body["academic_year"] is None
    # From the first release's year to the last, oldest first.
    assert body["columns"] == ["2024", "2025", "2026"]
    rows = _rows(body)
    assert rows["Ada Writer"]["counts"] == [0, 3, 1]
    # Anyone who ever wrote has a row, even after leaving.
    assert rows["Di Earlier"]["counts"] == [1, 0, 0]
    assert rows["Cy Former"]["counts"] == [0, 1, 0]
    assert body["totals"] == [1, 5, 1] and body["total"] == 7
    assert body["undated"] == 1


async def test_all_years_with_nothing_dated_show_the_current_year(client, admin_headers):
    body = await _get(client, admin_headers, all_years="true")
    current = academic_year(today_in((await _institution()).timezone), 4)
    assert body["columns"] == [str(current)] and body["total"] == 0


async def test_the_export_of_all_years(client, admin_headers, writers):
    response = await client.get(
        f"{URL}/export", headers=admin_headers, params={"all_years": "true", "format": "csv"}
    )
    assert response.status_code == 200, response.text
    assert 'filename="release_radar_writers_all_years_' in response.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert rows[0] == ["Writer", "AY2024", "AY2025", "AY2026", "Total"]
    assert rows[-1] == ["Total", "1", "5", "1", "7"]
    response = await client.get(
        f"{URL}/export", headers=admin_headers, params={"all_years": "true", "language": "ja"}
    )
    workbook = openpyxl.load_workbook(io.BytesIO(response.content))
    assert [cell.value for cell in workbook["ライター"][1]][1] == "2024年度"
    notes = "\n".join(
        str(row[0] or "") for row in workbook.worksheets[-1].iter_rows(values_only=True)
    )
    assert "すべての年度（2024年度〜2026年度）" in notes

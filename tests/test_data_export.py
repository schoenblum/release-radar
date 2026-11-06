"""Full export: all data, no secrets. Synthetic data."""

import io
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import openpyxl
import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Institution, Release, UserRole

URL = "/api/v1/settings/export"


@pytest.mark.parametrize("role", [UserRole.editor, UserRole.viewer])
async def test_the_full_export_is_for_admins(client, headers_for, role):
    assert (await client.get(URL, headers=await headers_for(role))).status_code == 403


async def _make_release(**values) -> Release:
    async with SessionLocal() as db:
        institution_id = await db.scalar(select(Institution.id))
        release = Release(institution_id=institution_id, **values)
        db.add(release)
        await db.commit()
        return release


@pytest.mark.parametrize("timezone", ["Pacific/Kiritimati", "Pacific/Pago_Pago"])
async def test_the_filename_carries_the_institutions_date(client, admin_headers, timezone):
    # These two zones are 25 hours apart, so they never share a date with each other.
    async with SessionLocal() as db:
        institution = await db.scalar(select(Institution))
        institution.timezone = timezone
        await db.commit()
    response = await client.get(URL, headers=admin_headers)
    today = datetime.now(ZoneInfo(timezone)).strftime("%Y%m%d")
    assert f'filename="release_radar_{today}.json"' in response.headers["content-disposition"]


async def test_json_export_has_the_data_and_no_secrets(client, admin_headers):
    await _make_release(title="安全なタイトル")
    response = await client.get(URL, headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert 'filename="release_radar_' in response.headers["content-disposition"]
    data = response.json()

    assert data["releases"][0]["title"] == "安全なタイトル"
    assert len(data["readings"]) == 5
    assert {row["key"] for row in data["checkpoints"]} == {"d0", "d28"}
    assert "audit_log" in data
    assert data["institutions"][0]["name_en"] == "Example University"

    assert "chief@example.org" in {row["email"] for row in data["users"]}
    text = response.text
    assert "password_hash" not in {key for row in data["users"] for key in row}
    assert "$2b$" not in text
    for table in ("refresh_tokens", "password_reset_tokens", "rate_limit_hits"):
        assert table not in data


async def test_xlsx_export_has_a_sheet_per_table_and_keeps_formulas_as_text(client, admin_headers):
    await _make_release(title="=SUM(A1:A9)", custom_values={"a": {"state": "value", "value": 1}})
    response = await client.get(URL, headers=admin_headers, params={"format": "xlsx"})
    assert response.status_code == 200
    assert "spreadsheetml" in response.headers["content-type"]
    workbook = openpyxl.load_workbook(io.BytesIO(response.content))
    assert {"releases", "readings", "users", "audit_log"} <= set(workbook.sheetnames)

    sheet = workbook["releases"]
    header = [cell.value for cell in sheet[1]]
    row = [cell for cell in sheet[2]]
    title = row[header.index("title")]
    assert title.value == "=SUM(A1:A9)"
    assert title.data_type == "s"
    assert json.loads(row[header.index("custom_values")].value)["a"]["value"] == 1
    assert "password_hash" not in [cell.value for cell in workbook["users"][1]]


async def test_an_unknown_format_is_refused(client, admin_headers):
    response = await client.get(URL, headers=admin_headers, params={"format": "pdf"})
    assert response.status_code == 422

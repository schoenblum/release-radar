"""Researcher feedback (R8.1.2, R11.4): the Microsoft Forms import and the dimensions.

The export is built here with the real form's headings and made-up people and answers.
"""

import base64
import io
from datetime import date, datetime, timedelta

import openpyxl
import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import AuditLog, Institution, Release, SurveyResponse, UserRole
from app.services.feedback import dimensions as dims
from app.services.feedback.template import ITEMS

URL = "/api/v1/imports/feedback"
Q = "How do you rate the English press release produced for you?."
HEADINGS = [
    "Id",
    "Start time",
    "Completion time",
    "Email",
    "Name",
    "Language",
    "First author on paper or primary researcher/contact",
    "Press release ID (provided in email)",
    "Date of release",
    "1",
    "Did any of the following activities result from inquiries about the English press release?",
    Q + "The production process was easy to understand and follow",
    Q + "The press release conveyed my research accurately",
    Q + "The press release was well written and easy to understand",
    "Any comments about the English press release service or suggestions for improvements.",
]
SA, A, SD = "Strongly agree", "Agree", "Strongly disagree"
ENGLISH = "English (United Kingdom)‎"


def _row(
    id_,
    ref,
    inquiries="None",
    activities="None",
    sats=(SA, SA, A),
    language="日本語",
    name=None,
    comment=None,
):
    return [
        id_,
        datetime(2026, 1, 5, 10, 0),
        # One minute apart, so the responses have an order.
        datetime(2026, 1, 5, 10, 0) + timedelta(minutes=id_),
        "anonymous",
        None,
        language,
        name or f"Researcher Example {id_}",
        ref,
        None,
        inquiries,
        activities,
        *sats,
        comment,
    ]


def _export(rows, headings=HEADINGS) -> dict:
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(headings)
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    book.save(buffer)
    return {
        "name": "Press release feedback form.xlsx",
        "content": base64.b64encode(buffer.getvalue()).decode(),
    }


ROWS = [
    _row(1, None, name="Office Test"),
    _row(
        2,
        "AY2025-011",
        "Journalists/media;Companies/businesses",
        "Joint research;Essays/articles",
        language=ENGLISH,
    ),
    _row(3, "AY2026-08)", "JST;Nagoya University students", "取材がメイン"),
    _row(4, "https://www.eurekalert.org/news-releases/1000042", "None", "None", (A, A, A)),
    _row(13, " AY2025-11", "General public", "None", (SD, SD, SD)),
    _row(5, "AY2024-99", "None", None, (SA, None, SA)),
    _row(70, "AY2026-08", "None", "None", (SD, SD, SD)),
]


@pytest.fixture
async def releases():
    async with SessionLocal() as db:
        institution_id = await db.scalar(select(Institution.id))
        made = {}
        for code, day, ea_url in (
            ("AY2025-11", date(2025, 6, 2), None),
            ("AY2026-08", date(2026, 5, 20), None),
            ("AY2025-30", date(2025, 9, 1), "https://www.eurekalert.org/news-releases/1000042"),
        ):
            release = Release(
                institution_id=institution_id,
                title=f"Synthetic {code}",
                code=code,
                release_date=day,
                ea_url=ea_url,
            )
            db.add(release)
            made[code] = release
        await db.commit()
        return {code: release.id for code, release in made.items()}


async def _run(client, headers, rows=ROWS, commit=False, **body):
    response = await client.post(
        URL, json={"file": _export(rows), "commit": commit, **body}, headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _responses() -> dict[str, SurveyResponse]:
    async with SessionLocal() as db:
        return {r.external_id: r for r in await db.scalars(select(SurveyResponse))}


async def test_a_check_says_what_would_happen_and_changes_nothing(client, admin_headers, releases):
    result = await _run(client, admin_headers)
    assert result["committed"] is False
    assert result["counts"] == {
        "feedback_rows": 7,
        "feedback_skipped": 1,
        "feedback_new": 6,
        "feedback_linked": 5,
        "feedback_not_linked": 1,
        "feedback_releases": 3,
        "feedback_corrected": 1,
        "feedback_other_texts": 2,
    }
    assert await _responses() == {}
    markdown = result["markdown"]
    assert markdown.startswith("# Researcher feedback import: dry run (nothing changed)")
    # Which column was read as what, and the inquiries column found by its content.
    assert "J: 1" in markdown and "Read as inquiries, by its content" in markdown
    assert "Read as activities, by its heading." in markdown
    assert "Read as AY2025-11." in markdown
    assert "Linked to the release with this EurekAlert link." in markdown
    assert "No release has this ID" in markdown
    # The new all-"Strongly disagree" response is listed, not corrected.
    assert "(response 70). An inverted scale" in markdown
    # Nobody is named in the report.
    assert "Researcher Example" not in markdown and "Office Test" not in markdown
    assert "Researcher Example" not in result["csv"]
    assert "Dashes" not in markdown


async def test_import_stores_the_answers_by_item_key(client, admin_headers, releases):
    result = await _run(client, admin_headers, commit=True)
    assert result["committed"] is True
    stored = await _responses()
    assert set(stored) == {"2", "3", "4", "5", "13", "70"}

    first = stored["2"]
    assert first.release_id == releases["AY2025-11"]
    assert first.language == "en"
    assert first.respondent_name == "Researcher Example 2"
    assert first.source == "legacy_import"
    # Completion time, read in the institution's time zone (JST).
    assert first.submitted_at.isoformat() == "2026-01-05T01:02:00+00:00"
    assert first.answers["inq_media"] is True and first.answers["inq_companies"] is True
    assert first.answers["inq_public"] is False and first.answers["inq_none"] is False
    assert first.answers["act_collab"] is True and first.answers["act_none"] is False
    assert (first.answers["sat_process"], first.answers["sat_understandability"]) == (5, 4)

    other = stored["3"]
    assert other.release_id == releases["AY2026-08"]
    assert other.other_texts == {"inquiries": "JST", "activities": "取材がメイン"}
    assert other.answers["inq_students_nu"] is True
    # Only an "other" answer: the question was answered, with nothing on the list ticked.
    assert not any(other.answers[key] for key in other.answers if key.startswith("act_"))

    assert stored["4"].release_id == releases["AY2025-30"]
    assert stored["4"].answers["inq_none"] is True
    # A skipped question has no keys at all: missing, not 0.
    skipped = stored["5"]
    assert skipped.release_id is None
    assert not any(key.startswith("act_") for key in skipped.answers)
    assert "sat_accuracy" not in skipped.answers
    # A new all-disagree response is kept as given.
    assert stored["70"].answers["sat_process"] == 1


async def test_the_four_inverted_responses_are_corrected_in_their_history(
    client, admin_headers, releases
):
    await _run(client, admin_headers, commit=True)
    corrected = (await _responses())["13"]
    assert [
        corrected.answers[k] for k in ("sat_process", "sat_accuracy", "sat_understandability")
    ] == [5, 5, 5]
    async with SessionLocal() as db:
        entries = list(
            await db.scalars(
                select(AuditLog)
                .where(AuditLog.entity_id == corrected.id)
                .order_by(AuditLog.created_at, AuditLog.field)
            )
        )
    created = next(entry for entry in entries if entry.action == "create")
    assert created.note == "feedback_import"
    assert created.new_value["answers"]["sat_accuracy"] == 1
    changes = {
        entry.field: (entry.old_value, entry.new_value, entry.note)
        for entry in entries
        if entry.action == "update"
    }
    assert changes == {
        f"answers.{key}": (1, 5, "inverted_scale_corrected")
        for key in ("sat_process", "sat_accuracy", "sat_understandability")
    }


async def test_a_new_export_adds_only_new_responses(client, admin_headers, releases):
    await _run(client, admin_headers, commit=True)
    async with SessionLocal() as db:
        kept = await db.scalar(select(SurveyResponse).where(SurveyResponse.external_id == "4"))
        kept.answers = {**kept.answers, "sat_process": 3}
        await db.commit()

    later = [*ROWS, _row(71, "AY2025-30", "Journalists/media", "Visits/meetings")]
    result = await _run(client, admin_headers, rows=later, commit=True)
    assert result["counts"]["feedback_already"] == 6
    assert result["counts"]["feedback_new"] == 1
    assert "feedback_corrected" not in result["counts"]
    stored = await _responses()
    assert set(stored) == {"2", "3", "4", "5", "13", "70", "71"}
    # Imported ones are left exactly as they are.
    assert stored["4"].answers["sat_process"] == 3


async def test_a_missing_column_is_named(client, admin_headers):
    headings = [h for h in HEADINGS if "conveyed" not in h]
    rows = [row[:12] + row[13:] for row in ROWS]
    response = await client.post(
        URL, json={"file": _export(rows, headings), "commit": False}, headers=admin_headers
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "import_column_missing"
    assert response.json()["column"] == "sat_accuracy"


async def test_a_file_that_is_not_a_workbook_is_explained(client, admin_headers):
    file = {"name": "x.xlsx", "content": base64.b64encode(b"not a workbook").decode()}
    response = await client.post(URL, json={"file": file}, headers=admin_headers)
    assert response.json()["detail"] == "import_not_a_workbook"


@pytest.mark.parametrize("role", [UserRole.editor, UserRole.viewer])
async def test_the_import_is_for_admins(client, headers_for, role):
    response = await client.post(URL, json={"file": _export(ROWS)}, headers=await headers_for(role))
    assert response.status_code == 403


async def test_the_history_keeps_each_kind_apart(client, admin_headers, releases):
    result = await _run(client, admin_headers)
    runs = (await client.get("/api/v1/imports?kind=feedback", headers=admin_headers)).json()
    assert [run["id"] for run in runs] == [result["run_id"]]
    assert runs[0]["kind"] == "feedback"
    assert (await client.get("/api/v1/imports?kind=workbook", headers=admin_headers)).json() == []
    report = await client.get(
        f"/api/v1/imports/{result['run_id']}/report?format=md&language=ja", headers=admin_headers
    )
    assert report.text.startswith("# 研究者アンケートのインポート：確認（変更なし）")
    assert "release_radar_feedback_dry_run_" in report.headers["content-disposition"]


async def test_the_record_shows_its_feedback_to_office_users(
    client, admin_headers, headers_for, releases
):
    await _run(client, admin_headers, commit=True)
    viewer = await headers_for(UserRole.viewer)
    answer = await client.get(f"/api/v1/releases/{releases['AY2025-11']}/feedback", headers=viewer)
    assert answer.status_code == 200
    shown = answer.json()
    assert [r["respondent_name"] for r in shown] == [
        "Researcher Example 2",
        "Researcher Example 13",
    ]
    assert shown[0]["template_name"] == "NU Forms 2025"
    assert [item["key"] for item in shown[0]["items"]] == [item.key for item in ITEMS]
    assert shown[1]["answers"]["sat_accuracy"] == 5
    assert (
        await client.get(f"/api/v1/releases/{releases['AY2025-11']}/feedback")
    ).status_code == 401


# ---------------------------------------------------------------- dimensions (R11.4)


ITEM_INFO = {
    item.key: dims.ItemInfo(item.question, item.exclusive, item.external) for item in ITEMS
}


def _answers(inquiries=(), activities=(), sats=None, skip=()):
    answers = {}
    if "inquiries" not in skip:
        answers.update({i.key: i.key in inquiries for i in ITEMS if i.question == "inquiries"})
    if "activities" not in skip:
        answers.update({i.key: i.key in activities for i in ITEMS if i.question == "activities"})
    answers.update(sats or {})
    return answers


def test_one_response_gives_the_mean_and_the_counts():
    found = dims.dimensions(
        [
            _answers(
                ("inq_media", "inq_researchers_nu"),
                ("act_collab",),
                {"sat_process": 5, "sat_accuracy": 4, "sat_understandability": 3},
            )
        ],
        ITEM_INFO,
    )
    assert found == dims.FeedbackDimensions(
        responses=1, satisfaction=4.0, research_outcomes=1, inquiries=2, inquiries_external=1
    )


def test_none_is_zero_and_a_skipped_question_is_missing():
    found = dims.dimensions([_answers(("inq_none",), skip=("activities",))], ITEM_INFO)
    assert (found.inquiries, found.inquiries_external) == (0, 0)
    assert found.research_outcomes is None
    assert found.satisfaction is None


def test_several_responses_take_the_mean_and_the_union():
    found = dims.dimensions(
        [
            _answers(("inq_media",), ("act_collab",), {"sat_process": 5, "sat_accuracy": 5}),
            _answers(("inq_media", "inq_public"), ("act_article",), {"sat_process": 3}),
        ],
        ITEM_INFO,
    )
    # Each response's own mean (5 and 3), then the mean of those.
    assert found.satisfaction == 4.0
    assert (found.research_outcomes, found.inquiries, found.inquiries_external) == (2, 2, 2)
    assert found.responses == 2


def test_a_release_without_a_response_is_missing():
    assert dims.dimensions([], ITEM_INFO) is None


async def test_dimensions_by_release_from_the_import(client, admin_headers, releases):
    await _run(client, admin_headers, commit=True)
    async with SessionLocal() as db:
        found = await dims.by_release(db, await db.scalar(select(Institution.id)))
    first = found[releases["AY2025-11"]]
    # Responses 2 (5, 5, 4) and 13 (corrected to 5, 5, 5).
    assert first.responses == 2
    assert first.satisfaction == pytest.approx((14 / 3 + 5) / 2)
    assert first.inquiries == 3  # media and companies, then the public
    assert first.inquiries_external == 3
    assert first.research_outcomes == 2
    assert set(found) == set(releases.values())

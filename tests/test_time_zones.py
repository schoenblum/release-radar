"""Release times across daylight saving (Daniel, 2026-11-13): every conversion uses the offset
in force on its own date, in zones whose clocks change on different days, north and south."""

import re
from datetime import date, time
from pathlib import Path

import pytest

from app.services.time_zones import BY_KEY, EASTERN, ZONES, convert, exists

JAPAN = "Asia/Tokyo"


@pytest.mark.parametrize(
    ("day", "clock", "source", "target", "expected"),
    [
        # US Eastern: daylight saving from 8 March to 1 November 2026 (UTC−5, then −4).
        ("2026-03-06", "10:00", EASTERN, JAPAN, ("2026-03-07", "00:00")),
        ("2026-03-09", "10:00", EASTERN, JAPAN, ("2026-03-09", "23:00")),
        ("2026-10-30", "10:00", EASTERN, JAPAN, ("2026-10-30", "23:00")),
        ("2026-11-02", "10:00", EASTERN, JAPAN, ("2026-11-03", "00:00")),
        # The UK changes three weeks after the US, on 29 March: GMT, then BST.
        ("2026-03-20", "18:00", JAPAN, "Europe/London", ("2026-03-20", "09:00")),
        ("2026-03-30", "18:00", JAPAN, "Europe/London", ("2026-03-30", "10:00")),
        # Sydney, in the south, the other way round: summer time until 5 April, again from
        # 4 October (UTC+11, else +10).
        ("2026-04-03", "12:00", JAPAN, "Australia/Sydney", ("2026-04-03", "14:00")),
        ("2026-04-06", "12:00", JAPAN, "Australia/Sydney", ("2026-04-06", "13:00")),
        ("2026-10-02", "12:00", JAPAN, "Australia/Sydney", ("2026-10-02", "13:00")),
        ("2026-10-05", "12:00", JAPAN, "Australia/Sydney", ("2026-10-05", "14:00")),
        # Japan keeps one time all year: there and back gives what went in.
        ("2026-07-01", "00:30", JAPAN, EASTERN, ("2026-06-30", "11:30")),
    ],
)
def test_each_date_converts_with_its_own_offset(day, clock, source, target, expected):
    found_day, found_time = convert(
        date.fromisoformat(day), time.fromisoformat(clock), source, target
    )
    assert (found_day.isoformat(), found_time.strftime("%H:%M")) == expected
    back = convert(found_day, found_time, target, source)
    assert (back[0].isoformat(), back[1].strftime("%H:%M")) == (day, clock)


def test_the_hour_the_clocks_skip_does_not_exist():
    assert exists(date(2026, 3, 8), time(2, 30), EASTERN) is False
    assert exists(date(2026, 3, 8), time(3, 30), EASTERN) is True
    assert exists(date(2026, 3, 29), time(1, 30), "Europe/London") is False
    # The hour that happens twice exists, and is read as the first time round.
    assert exists(date(2026, 11, 1), time(1, 30), EASTERN) is True
    assert convert(date(2026, 11, 1), time(1, 30), EASTERN, JAPAN) == (
        date(2026, 11, 1),
        time(14, 30),
    )
    # Japan has no such hour.
    assert exists(date(2026, 3, 8), time(2, 30), JAPAN) is True


def test_the_list_is_a_list_of_zones_and_the_page_has_the_same():
    """Daniel, 2026-11-13: a list of time zones, not every city. The page lists the same."""
    assert 20 <= len(ZONES) <= 40
    assert len(BY_KEY) == len(ZONES)
    page = Path(__file__).resolve().parents[1] / "frontend" / "src" / "timeZones.ts"
    listed = re.findall(r'key: "([^"]+)"', page.read_text(encoding="utf-8"))
    listed += ["America/New_York"] if "key: EASTERN" in page.read_text(encoding="utf-8") else []
    assert sorted(listed) == sorted(BY_KEY)

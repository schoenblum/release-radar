"""Release times: kept in the institution's time zone, entered and shown in a few others.

A release time is stored in the institution's zone (Japan time for NU), because that is what
the website and the researchers go by (Daniel, 2026-11-12). EurekAlert works in US Eastern
time, so a date and time can be entered in another zone: both are then converted, and the date
can move by a day. Admins choose up to three further zones to show a release time in.

``frontend/src/timeZones.ts`` mirrors this list.
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

EASTERN = "America/New_York"
MAX_SHOWN = 3


@dataclass(frozen=True)
class Zone:
    key: str  # IANA name
    short: str
    name_en: str
    name_ja: str


ZONES: tuple[Zone, ...] = (
    Zone("Asia/Tokyo", "JST", "Japan", "日本時間"),
    Zone(EASTERN, "ET", "US Eastern", "米国東部時間"),
    Zone("America/Los_Angeles", "PT", "US Pacific", "米国太平洋時間"),
    Zone("Europe/London", "UK", "UK", "英国時間"),
    Zone("Europe/Paris", "CET", "Central Europe", "中央ヨーロッパ時間"),
    Zone("Australia/Sydney", "AET", "Australia Eastern", "オーストラリア東部時間"),
    Zone("UTC", "UTC", "UTC", "協定世界時"),
)
BY_KEY = {zone.key: zone for zone in ZONES}


def short_label(key: str) -> str:
    """JST, ET … for the listed zones; the IANA name for any other."""
    zone = BY_KEY.get(key)
    return zone.short if zone else key


def convert(day: date, clock: time, source: str, target: str) -> tuple[date, time]:
    """A date and time in one zone, as the date and time in another."""
    moment = datetime.combine(day, clock.replace(tzinfo=None), tzinfo=ZoneInfo(source))
    moved = moment.astimezone(ZoneInfo(target))
    return moved.date(), moved.time().replace(tzinfo=None)

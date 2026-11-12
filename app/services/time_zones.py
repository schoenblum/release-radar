"""Release times: kept in the institution's time zone, entered and shown in a few others.

A release time is stored in the institution's zone (Japan time for NU), because that is what
the website and the researchers go by (Daniel, 2026-11-12). EurekAlert works in US Eastern
time, so a date and time can be entered in another zone: both are then converted, and the date
can move by a day. Admins choose up to three further zones to show a release time in, from the
list below, in the order they want them (Daniel, 2026-11-13: a list of time zones, not every
city in the time-zone database).

Every conversion goes through the IANA time-zone database (``zoneinfo``), which holds each
zone's daylight-saving rules and their history, so a date and time is always converted with
the offset in force on that date. A time the clocks skip when daylight saving starts does not
exist and is refused (``exists``); a time that happens twice when it ends is read as the first.

``frontend/src/timeZones.ts`` mirrors this list (a test checks the keys).
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

EASTERN = "America/New_York"
MAX_SHOWN = 3


@dataclass(frozen=True)
class Zone:
    key: str  # IANA name
    short: str
    name_en: str
    name_ja: str


# West to east. One zone per region people work with; zones that keep the same time all year
# and share an offset are still listed apart when people know them by name.
ZONES: tuple[Zone, ...] = (
    Zone("Pacific/Honolulu", "HT", "Hawaii", "ハワイ時間"),
    Zone("America/Anchorage", "AKT", "Alaska", "アラスカ時間"),
    Zone("America/Los_Angeles", "PT", "US Pacific", "米国太平洋時間"),
    Zone("America/Denver", "MT", "US Mountain", "米国山岳部時間"),
    Zone("America/Chicago", "CT", "US Central", "米国中部時間"),
    Zone("America/Mexico_City", "MEX", "Mexico City", "メキシコシティ時間"),
    Zone(EASTERN, "ET", "US Eastern", "米国東部時間"),
    Zone("America/Halifax", "AT", "Atlantic (Canada)", "大西洋時間（カナダ）"),
    Zone("America/Sao_Paulo", "BRT", "Brazil (São Paulo)", "ブラジル時間（サンパウロ）"),
    Zone("America/Argentina/Buenos_Aires", "ART", "Argentina", "アルゼンチン時間"),
    Zone("UTC", "UTC", "UTC", "協定世界時"),
    Zone("Europe/London", "UK", "UK", "英国時間"),
    Zone("Africa/Lagos", "WAT", "West Africa", "西アフリカ時間"),
    Zone("Europe/Paris", "CET", "Central Europe", "中央ヨーロッパ時間"),
    Zone("Europe/Helsinki", "EET", "Eastern Europe", "東ヨーロッパ時間"),
    Zone("Africa/Johannesburg", "SAST", "South Africa", "南アフリカ時間"),
    Zone("Europe/Istanbul", "TRT", "Turkey", "トルコ時間"),
    Zone("Europe/Moscow", "MSK", "Moscow", "モスクワ時間"),
    Zone("Africa/Nairobi", "EAT", "East Africa", "東アフリカ時間"),
    Zone("Asia/Dubai", "GST", "Gulf (Dubai)", "湾岸時間（ドバイ）"),
    Zone("Asia/Karachi", "PKT", "Pakistan", "パキスタン時間"),
    Zone("Asia/Kolkata", "IST", "India", "インド時間"),
    Zone("Asia/Bangkok", "ICT", "Indochina (Bangkok, Hanoi)", "インドシナ時間（バンコク・ハノイ）"),
    Zone(
        "Asia/Jakarta", "WIB", "Western Indonesia (Jakarta)", "インドネシア西部時間（ジャカルタ）"
    ),
    Zone("Asia/Shanghai", "CN", "China", "中国時間"),
    Zone("Asia/Hong_Kong", "HKT", "Hong Kong", "香港時間"),
    Zone("Asia/Taipei", "TW", "Taiwan", "台湾時間"),
    Zone("Asia/Singapore", "SGT", "Singapore", "シンガポール時間"),
    Zone("Australia/Perth", "AWST", "Australia Western", "オーストラリア西部時間"),
    Zone("Asia/Seoul", "KST", "Korea", "韓国時間"),
    Zone("Asia/Tokyo", "JST", "Japan", "日本時間"),
    Zone("Australia/Adelaide", "ACT", "Australia Central", "オーストラリア中部時間"),
    Zone("Australia/Sydney", "AET", "Australia Eastern", "オーストラリア東部時間"),
    Zone("Pacific/Auckland", "NZT", "New Zealand", "ニュージーランド時間"),
)
BY_KEY = {zone.key: zone for zone in ZONES}


def short_label(key: str) -> str:
    """JST, ET … for the listed zones; the IANA name for any other."""
    zone = BY_KEY.get(key)
    return zone.short if zone else key


def exists(day: date, clock: time, zone: str) -> bool:
    """Whether a wall-clock time happens in a zone on that day. False only for the hour the
    clocks skip when daylight saving starts, such as 02:30 US Eastern on 8 March 2026."""
    moment = datetime.combine(day, clock.replace(tzinfo=None), tzinfo=ZoneInfo(zone))
    back = moment.astimezone(UTC).astimezone(ZoneInfo(zone))
    return back.replace(tzinfo=None) == moment.replace(tzinfo=None)


def convert(day: date, clock: time, source: str, target: str) -> tuple[date, time]:
    """A date and time in one zone, as the date and time in another, each with the offset in
    force on that date (daylight saving included). A time that happens twice, when daylight
    saving ends, is read as the first; check ``exists`` first for a time someone typed."""
    moment = datetime.combine(day, clock.replace(tzinfo=None), tzinfo=ZoneInfo(source))
    moved = moment.astimezone(ZoneInfo(target))
    return moved.date(), moved.time().replace(tzinfo=None)

/**
 * Release times: kept in the institution's time zone (Japan time for NU), entered and shown in
 * up to three others, in the order an admin chooses, from a list of time zones (Daniel,
 * 2026-11-12 and -13). Mirrors `app/services/time_zones.py`; a test checks the keys.
 *
 * Conversions go through the browser's copy of the IANA time-zone database (`Intl`), which
 * holds each zone's daylight-saving rules: every date is converted with the offset in force on
 * that date.
 */

export interface Zone {
  key: string; // IANA name
  short: string;
  nameEn: string;
  nameJa: string;
  /** What people type after a time to mean this zone. */
  words: string[];
}

export const EASTERN = "America/New_York";
export const MAX_SHOWN = 3;

// West to east, as on the server.
export const ZONES: Zone[] = [
  { key: "Pacific/Honolulu", short: "HT", nameEn: "Hawaii", nameJa: "ハワイ時間", words: ["hst", "hawaii"] },
  { key: "America/Anchorage", short: "AKT", nameEn: "Alaska", nameJa: "アラスカ時間", words: ["akst", "akdt", "alaska"] },
  { key: "America/Los_Angeles", short: "PT", nameEn: "US Pacific", nameJa: "米国太平洋時間", words: ["pst", "pdt", "pacific"] },
  { key: "America/Denver", short: "MT", nameEn: "US Mountain", nameJa: "米国山岳部時間", words: ["mst", "mdt", "mountain"] },
  { key: "America/Chicago", short: "CT", nameEn: "US Central", nameJa: "米国中部時間", words: ["cst", "cdt", "central"] },
  { key: "America/Mexico_City", short: "MEX", nameEn: "Mexico City", nameJa: "メキシコシティ時間", words: ["mexico"] },
  { key: EASTERN, short: "ET", nameEn: "US Eastern", nameJa: "米国東部時間", words: ["est", "edt", "eastern", "東部時間"] },
  { key: "America/Halifax", short: "AT", nameEn: "Atlantic (Canada)", nameJa: "大西洋時間（カナダ）", words: ["ast", "adt", "atlantic"] },
  { key: "America/Sao_Paulo", short: "BRT", nameEn: "Brazil (São Paulo)", nameJa: "ブラジル時間（サンパウロ）", words: ["brazil"] },
  { key: "America/Argentina/Buenos_Aires", short: "ART", nameEn: "Argentina", nameJa: "アルゼンチン時間", words: ["argentina"] },
  { key: "UTC", short: "UTC", nameEn: "UTC", nameJa: "協定世界時", words: ["gmt+0", "z"] },
  { key: "Europe/London", short: "UK", nameEn: "UK", nameJa: "英国時間", words: ["gmt", "bst", "london"] },
  { key: "Africa/Lagos", short: "WAT", nameEn: "West Africa", nameJa: "西アフリカ時間", words: [] },
  { key: "Europe/Paris", short: "CET", nameEn: "Central Europe", nameJa: "中央ヨーロッパ時間", words: ["cest"] },
  { key: "Europe/Helsinki", short: "EET", nameEn: "Eastern Europe", nameJa: "東ヨーロッパ時間", words: ["eest"] },
  { key: "Africa/Johannesburg", short: "SAST", nameEn: "South Africa", nameJa: "南アフリカ時間", words: [] },
  { key: "Europe/Istanbul", short: "TRT", nameEn: "Turkey", nameJa: "トルコ時間", words: [] },
  { key: "Europe/Moscow", short: "MSK", nameEn: "Moscow", nameJa: "モスクワ時間", words: [] },
  { key: "Africa/Nairobi", short: "EAT", nameEn: "East Africa", nameJa: "東アフリカ時間", words: [] },
  { key: "Asia/Dubai", short: "GST", nameEn: "Gulf (Dubai)", nameJa: "湾岸時間（ドバイ）", words: ["dubai"] },
  { key: "Asia/Karachi", short: "PKT", nameEn: "Pakistan", nameJa: "パキスタン時間", words: [] },
  { key: "Asia/Kolkata", short: "IST", nameEn: "India", nameJa: "インド時間", words: ["india"] },
  { key: "Asia/Bangkok", short: "ICT", nameEn: "Indochina (Bangkok, Hanoi)", nameJa: "インドシナ時間（バンコク・ハノイ）", words: [] },
  { key: "Asia/Jakarta", short: "WIB", nameEn: "Western Indonesia (Jakarta)", nameJa: "インドネシア西部時間（ジャカルタ）", words: [] },
  { key: "Asia/Shanghai", short: "CN", nameEn: "China", nameJa: "中国時間", words: ["china", "beijing", "中国"] },
  { key: "Asia/Hong_Kong", short: "HKT", nameEn: "Hong Kong", nameJa: "香港時間", words: [] },
  { key: "Asia/Taipei", short: "TW", nameEn: "Taiwan", nameJa: "台湾時間", words: ["taiwan", "台湾"] },
  { key: "Asia/Singapore", short: "SGT", nameEn: "Singapore", nameJa: "シンガポール時間", words: [] },
  { key: "Australia/Perth", short: "AWST", nameEn: "Australia Western", nameJa: "オーストラリア西部時間", words: [] },
  { key: "Asia/Seoul", short: "KST", nameEn: "Korea", nameJa: "韓国時間", words: ["korea", "韓国"] },
  { key: "Asia/Tokyo", short: "JST", nameEn: "Japan", nameJa: "日本時間", words: ["japan", "日本"] },
  { key: "Australia/Adelaide", short: "ACT", nameEn: "Australia Central", nameJa: "オーストラリア中部時間", words: ["acst", "acdt"] },
  { key: "Australia/Sydney", short: "AET", nameEn: "Australia Eastern", nameJa: "オーストラリア東部時間", words: ["aest", "aedt"] },
  { key: "Pacific/Auckland", short: "NZT", nameEn: "New Zealand", nameJa: "ニュージーランド時間", words: ["nzst", "nzdt"] },
];

const BY_KEY = new Map(ZONES.map((zone) => [zone.key, zone]));

/** "Berlin" for Europe/Berlin: a zone off the list, kept from before, still has a label. */
function cityOf(key: string): string {
  return (key.split("/").pop() ?? key).replaceAll("_", " ");
}

/** ET, JST … for the listed zones; the city for any other. */
export function shortLabel(key: string): string {
  return BY_KEY.get(key)?.short ?? cityOf(key);
}

/** "US Eastern (ET)", "米国東部時間（ET）"; a zone off the list by its IANA name. */
export function zoneName(key: string, language: string): string {
  const zone = BY_KEY.get(key);
  if (!zone) return key.replaceAll("_", " ");
  if (language === "ja") return `${zone.nameJa}（${zone.short}）`;
  // "UTC", "UK": the short label says nothing more.
  return zone.short === zone.nameEn ? zone.nameEn : `${zone.nameEn} (${zone.short})`;
}

/** A zone's offset from UTC at an instant, in minutes east. */
function offsetAt(key: string, instant: Date): number {
  const name =
    new Intl.DateTimeFormat("en-US", { timeZone: key, timeZoneName: "longOffset" })
      .formatToParts(instant)
      .find((part) => part.type === "timeZoneName")?.value ?? "GMT";
  const match = /GMT([+-])(\d{2}):?(\d{2})?/.exec(name);
  if (!match) return 0;
  const minutes = Number(match[2]) * 60 + Number(match[3] ?? 0);
  return match[1] === "-" ? -minutes : minutes;
}

/** A zone's standard offset: the smaller of winter's and summer's, as daylight saving adds. */
export function standardOffset(key: string, year = new Date().getFullYear()): number {
  return Math.min(
    offsetAt(key, new Date(Date.UTC(year, 0, 15))),
    offsetAt(key, new Date(Date.UTC(year, 6, 15))),
  );
}

/** "UTC−05:00", "UTC+09:30", "UTC±00:00". */
export function offsetLabel(minutes: number): string {
  const sign = minutes > 0 ? "+" : minutes < 0 ? "−" : "±";
  const size = Math.abs(minutes);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `UTC${sign}${pad(Math.floor(size / 60))}:${pad(size % 60)}`;
}

/** The listed zones, west to east by standard offset, without the one left out. */
export function zoneChoices(leaveOut?: string): Zone[] {
  return ZONES.filter((zone) => zone.key !== leaveOut)
    .map((zone, place) => ({ zone, place, offset: standardOffset(zone.key) }))
    .sort((a, b) => a.offset - b.offset || a.place - b.place)
    .map(({ zone }) => zone);
}

/** The listed zone a typed word means, if any: ET, JST, "eastern", "london" … */
export function zoneFromWord(word: string): string | null {
  const clean = word.normalize("NFKC").trim().toLowerCase();
  return (
    ZONES.find(
      (zone) =>
        zone.short.toLowerCase() === clean ||
        zone.nameEn.toLowerCase() === clean ||
        zone.nameJa === clean ||
        zone.words.includes(clean),
    )?.key ?? null
  );
}

/** The wall-clock date and time of an instant in a zone, as numbers. */
function partsIn(instant: number, zone: string) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: zone,
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).formatToParts(new Date(instant));
  const get = (type: string) => Number(parts.find((part) => part.type === type)?.value);
  return {
    year: get("year"),
    month: get("month"),
    day: get("day"),
    hour: get("hour") % 24,
    minute: get("minute"),
  };
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

/**
 * A date (YYYY-MM-DD) and time (HH:MM) in one zone, as the date and time in another. The
 * offset is found by trying: twice is enough, as an offset only changes once around an instant.
 */
export function convert(
  date: string,
  time: string,
  from: string,
  to: string,
): { date: string; time: string } {
  const [year, month, day] = date.split("-").map(Number);
  const [hour, minute] = time.split(":").map(Number);
  const wall = Date.UTC(year, month - 1, day, hour, minute);
  let instant = wall;
  for (let round = 0; round < 2; round += 1) {
    const seen = partsIn(instant, from);
    const seenWall = Date.UTC(seen.year, seen.month - 1, seen.day, seen.hour, seen.minute);
    instant += wall - seenWall;
  }
  const there = partsIn(instant, to);
  return {
    date: `${there.year}-${pad(there.month)}-${pad(there.day)}`,
    time: `${pad(there.hour)}:${pad(there.minute)}`,
  };
}

/**
 * A release's date and time in each further zone: "00:10 ET (2026-11-10)". The date is named
 * only where it differs from the release date.
 */
export function inOtherZones(
  date: string | null,
  time: string | null,
  local: string | undefined,
  zones: string[],
): string[] {
  if (!date || !time || !local) return [];
  return zones
    .filter((zone) => zone !== local)
    .map((zone) => {
      const there = convert(date, time.slice(0, 5), local, zone);
      const day = there.date === date ? "" : ` (${there.date})`;
      return `${there.time} ${shortLabel(zone)}${day}`;
    });
}

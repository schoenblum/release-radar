/**
 * Release times: kept in the institution's time zone (Japan time for NU), entered and shown in
 * a few others (Daniel, 2026-11-12). Mirrors `app/services/time_zones.py`.
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

export const ZONES: Zone[] = [
  { key: "Asia/Tokyo", short: "JST", nameEn: "Japan", nameJa: "日本時間", words: ["jst", "japan", "日本時間", "日本"] },
  { key: EASTERN, short: "ET", nameEn: "US Eastern", nameJa: "米国東部時間", words: ["et", "est", "edt", "eastern", "東部時間", "米国東部時間"] },
  { key: "America/Los_Angeles", short: "PT", nameEn: "US Pacific", nameJa: "米国太平洋時間", words: ["pt", "pst", "pdt", "pacific"] },
  { key: "Europe/London", short: "UK", nameEn: "UK", nameJa: "英国時間", words: ["uk", "gmt", "bst", "london"] },
  { key: "Europe/Paris", short: "CET", nameEn: "Central Europe", nameJa: "中央ヨーロッパ時間", words: ["cet", "cest"] },
  { key: "Australia/Sydney", short: "AET", nameEn: "Australia Eastern", nameJa: "オーストラリア東部時間", words: ["aet", "aest", "aedt"] },
  { key: "UTC", short: "UTC", nameEn: "UTC", nameJa: "協定世界時", words: ["utc"] },
];

const BY_KEY = new Map(ZONES.map((zone) => [zone.key, zone]));

export function shortLabel(key: string): string {
  return BY_KEY.get(key)?.short ?? key;
}

/** "US Eastern (ET)", "米国東部時間（ET）". */
export function zoneName(key: string, language: string): string {
  const zone = BY_KEY.get(key);
  if (!zone) return key;
  return language === "ja" ? `${zone.nameJa}（${zone.short}）` : `${zone.nameEn} (${zone.short})`;
}

/** The zone a typed word means, if any. */
export function zoneFromWord(word: string): string | null {
  const clean = word.normalize("NFKC").trim().toLowerCase();
  return ZONES.find((zone) => zone.words.includes(clean))?.key ?? null;
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

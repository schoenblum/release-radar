/**
 * Dates show as YYYY-MM-DD in both languages (R5.4.6), in the institution's time zone. The
 * Swedish locale is simply the standard way to get that format from the browser.
 */
const ISO_LOCALE = "sv-SE";

export function formatDate(value: string, timeZone?: string): string {
  return new Intl.DateTimeFormat(ISO_LOCALE, {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(value));
}

export function formatDateTime(value: string, timeZone?: string): string {
  return new Intl.DateTimeFormat(ISO_LOCALE, {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

/** An academic year as people write it: `AY2025`, or `2025年度` in Japanese (R5.4.6). */
export function academicYearLabel(year: number, language: string): string {
  return language === "ja" ? `${year}年度` : `AY${year}`;
}

const MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];

function iso(year: number, month: number, day: number): string | null {
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1) return null;
  if (date.getUTCDate() !== day) return null;
  return `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function fullYear(text: string): number {
  return text.length <= 2 ? 2000 + Number(text) : Number(text);
}

function todayIso(today: Date): string {
  return iso(today.getFullYear(), today.getMonth() + 1, today.getDate()) ?? "";
}

function daysApart(a: string, b: string): number {
  return Math.abs(Date.parse(a) - Date.parse(b)) / 86_400_000;
}

/**
 * Three numbers, read as people in Japan and elsewhere write them, never US style when another
 * reading works (Daniel, 2026-11-12). A four-digit year says where the year is. A two-digit
 * year is the first number (Japanese order) or the last (day, month, year): if just one of
 * them is this year, last year or next year, that one is the year; otherwise the reading
 * closest to today wins.
 */
function fromNumbers(first: string, middle: string, last: string, today: Date): string | null {
  const [a, b, c] = [Number(first), Number(middle), Number(last)];
  if (first.length === 4) return iso(a, b, c);
  if (last.length === 4) return iso(c, b, a) ?? iso(c, a, b);
  const yearFirst = first.length === 2 ? iso(fullYear(first), b, c) : null;
  const yearLast = last.length === 2 ? iso(fullYear(last), b, a) : null;
  if (yearFirst && yearLast) {
    const thisYear = today.getFullYear();
    const near = (text: string) => Math.abs(fullYear(text) - thisYear) <= 1;
    if (near(first) && !near(last)) return yearFirst;
    if (near(last) && !near(first)) return yearLast;
    const now = todayIso(today);
    return daysApart(yearLast, now) < daysApart(yearFirst, now) ? yearLast : yearFirst;
  }
  return yearFirst ?? yearLast ?? (last.length === 2 ? iso(fullYear(last), a, b) : null);
}

function monthOf(word: string): number {
  return MONTHS.indexOf(word.slice(0, 3).toLowerCase()) + 1;
}

/**
 * A date as it arrives by hand or by paste, as YYYY-MM-DD: 2026-11-10, 26/11/10, 10.11.26,
 * 10/11/2026, 2026年11月10日, 10-Nov-26, Nov 10, 2026. Anything else goes to the server
 * unchanged, which refuses it with an explanation.
 */
export function normaliseDate(text: string, today: Date = new Date()): string {
  const clean = text.normalize("NFKC").trim();
  const numbers = /^(\d{1,4})\s*[-/.\s]\s*(\d{1,2})\s*[-/.\s]\s*(\d{1,4})$/.exec(clean);
  if (numbers) return fromNumbers(numbers[1], numbers[2], numbers[3], today) ?? clean;
  const compact = /^(\d{4})(\d{2})(\d{2})$/.exec(clean);
  if (compact) return iso(+compact[1], +compact[2], +compact[3]) ?? clean;
  const japanese = /^(\d{2}|\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日?$/.exec(clean);
  if (japanese) return iso(fullYear(japanese[1]), +japanese[2], +japanese[3]) ?? clean;
  const dayFirst = /^(\d{1,2})(?:st|nd|rd|th)?[-\s.]*([A-Za-z]{3,9})\.?[-\s,.]*(\d{2}|\d{4})$/.exec(clean);
  if (dayFirst && monthOf(dayFirst[2]) > 0) {
    return iso(fullYear(dayFirst[3]), monthOf(dayFirst[2]), +dayFirst[1]) ?? clean;
  }
  const monthFirst = /^([A-Za-z]{3,9})\.?[-\s.]*(\d{1,2})(?:st|nd|rd|th)?[-\s,.]+(\d{2}|\d{4})$/.exec(clean);
  if (monthFirst && monthOf(monthFirst[1]) > 0) {
    return iso(fullYear(monthFirst[3]), monthOf(monthFirst[1]), +monthFirst[2]) ?? clean;
  }
  return clean;
}

export function isIsoDate(text: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(text);
}

export interface Clock {
  /** As the server takes it: H:MM, with seconds when given. */
  time: string;
  /** The zone it was given in, when one was named. */
  zone: string | null;
}

/**
 * A time with perhaps a zone after it: 10:00, 10:00 ET, 2:30 pm JST, 14時10分, 1000 ET.
 * Null when it isn't one; the server then explains.
 */
export function parseClock(text: string, zoneFromWord: (word: string) => string | null): Clock | null {
  const clean = text.normalize("NFKC").trim();
  const match =
    /^(\d{1,2})(?:[:時](\d{2})(?::(\d{2}))?分?|(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?\s*(.*)$/i.exec(clean);
  if (!match) return null;
  const [, hourText, colonMinutes, seconds, compactMinutes, half, rest] = match;
  const minutes = colonMinutes ?? compactMinutes;
  if (minutes === undefined && !half) return null;
  let hour = Number(hourText);
  if (half) {
    if (hour < 1 || hour > 12) return null;
    hour = (hour % 12) + (/^p/i.test(half) ? 12 : 0);
  }
  const zone = rest ? zoneFromWord(rest) : null;
  if (rest && zone === null) return null;
  const time = `${String(hour).padStart(2, "0")}:${minutes ?? "00"}${seconds ? `:${seconds}` : ""}`;
  return { time, zone };
}

export interface Moment {
  date: string;
  time: string | null;
  zone: string | null;
}

/**
 * A date with perhaps a time and a zone after it, as pasted from an embargo notice:
 * "10 Nov 2026, 10:00 ET", "2026-11-10 10:00", "2026/11/10 ET". Null when the date isn't one.
 */
export function parseMoment(
  text: string,
  zoneFromWord: (word: string) => string | null,
  today: Date = new Date(),
): Moment | null {
  const clean = text.normalize("NFKC").trim();
  const date = normaliseDate(clean, today);
  if (isIsoDate(date)) return { date, time: null, zone: null };
  // The time is the last thing with a colon (or 時) in it; a zone may follow it.
  const timed = /^(.*?)[\s,]*(?:at\s+)?(\d{1,2}[:時]\d{2}.*)$/i.exec(clean);
  if (timed) {
    const day = normaliseDate(timed[1].replace(/[\s,]+$/, ""), today);
    const clock = parseClock(timed[2], zoneFromWord);
    if (isIsoDate(day) && clock) return { date: day, time: clock.time, zone: clock.zone };
  }
  // A date and a zone alone: the release's time, read in that zone, stays.
  const zoned = /^(.*\S)\s+(\S+)$/.exec(clean);
  if (zoned) {
    const day = normaliseDate(zoned[1], today);
    const zone = zoneFromWord(zoned[2]);
    if (isIsoDate(day) && zone) return { date: day, time: null, zone };
  }
  return null;
}

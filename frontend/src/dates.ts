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

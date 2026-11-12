import type { Release } from "../../api/types";
import { normaliseDate, parseClock, parseMoment } from "../../dates";
import { zoneFromWord } from "../../timeZones";

/**
 * What to send for a release date or time typed as text (Daniel, 2026-11-12). Kept in the
 * institution's zone: a date and time typed in another one go together as
 * {date, time, zone}, and the server converts them, moving the date if need be. ``zone`` is
 * the zone chosen beside the field; a zone typed after the time wins.
 */
export function releaseDateValue(text: string, zone: string, local: string): unknown {
  if (text.trim() === "") return null;
  const moment = parseMoment(text, zoneFromWord);
  if (!moment) return normaliseDate(text);
  const given = moment.zone ?? zone;
  if (moment.time === null && given === local) return moment.date;
  return { date: moment.date, ...(moment.time ? { time: moment.time } : {}), zone: given };
}

export function releaseTimeValue(text: string, zone: string, local: string): unknown {
  if (text.trim() === "") return null;
  const clock = parseClock(text, zoneFromWord);
  if (!clock) return text;
  const given = clock.zone ?? zone;
  return given === local ? clock.time : { time: clock.time, zone: given };
}

/**
 * What undo puts back: the date and the time together, as a converted entry can have moved
 * both.
 */
export function releaseMomentSnapshot(
  release: Release,
  field: "release_date" | "release_time",
  local: string,
): { field: string; value: unknown } {
  if (release.release_date === null) return { field, value: release[field] };
  return {
    field: "release_date",
    value: { date: release.release_date, time: release.release_time, zone: local },
  };
}

/** HH:MM, as a release time shows. */
export function shownTime(time: string | null): string {
  return time?.slice(0, 5) ?? "";
}

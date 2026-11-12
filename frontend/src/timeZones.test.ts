import { describe, expect, it } from "vitest";

import {
  convert,
  inOtherZones,
  offsetLabel,
  shortLabel,
  standardOffset,
  zoneChoices,
  zoneFromWord,
  zoneName,
  ZONES,
} from "./timeZones";

const JAPAN = "Asia/Tokyo";
const EASTERN = "America/New_York";

describe("release times across daylight saving (Daniel, 2026-11-13)", () => {
  it.each([
    // US Eastern: daylight saving from 8 March to 1 November 2026.
    ["2026-03-07", "00:00", EASTERN, "2026-03-06 10:00"],
    ["2026-03-09", "23:00", EASTERN, "2026-03-09 10:00"],
    ["2026-10-30", "23:00", EASTERN, "2026-10-30 10:00"],
    ["2026-11-03", "00:00", EASTERN, "2026-11-02 10:00"],
    // The UK changes three weeks later, on 29 March.
    ["2026-03-20", "18:00", "Europe/London", "2026-03-20 09:00"],
    ["2026-03-30", "18:00", "Europe/London", "2026-03-30 10:00"],
    // Sydney, in the south: summer time until 5 April, again from 4 October.
    ["2026-04-03", "12:00", "Australia/Sydney", "2026-04-03 14:00"],
    ["2026-04-06", "12:00", "Australia/Sydney", "2026-04-06 13:00"],
    ["2026-10-02", "12:00", "Australia/Sydney", "2026-10-02 13:00"],
    ["2026-10-05", "12:00", "Australia/Sydney", "2026-10-05 14:00"],
  ])("Japan %s %s is %s %s", (date, time, zone, expected) => {
    const there = convert(date, time, JAPAN, zone);
    expect(`${there.date} ${there.time}`).toBe(expected);
    // And back: the same as the server's conversion the other way.
    const back = convert(there.date, there.time, zone, JAPAN);
    expect(`${back.date} ${back.time}`).toBe(`${date} ${time}`);
  });

  it("shows a release time in each further zone, in the order chosen", () => {
    expect(
      inOtherZones("2026-11-10", "14:10:00", JAPAN, ["Europe/Paris", EASTERN]),
    ).toEqual(["06:10 CET", "00:10 ET"]);
    // In July, the same Japan time is an hour later in both.
    expect(inOtherZones("2026-07-10", "14:10:00", JAPAN, ["Europe/Paris", EASTERN])).toEqual([
      "07:10 CET",
      "01:10 ET",
    ]);
  });
});

describe("the list of time zones (Daniel, 2026-11-13)", () => {
  it("is a list of zones, not every city, west to east by standard time", () => {
    expect(ZONES.length).toBeLessThan(40);
    const choices = zoneChoices(JAPAN);
    expect(choices.map((zone) => zone.key)).not.toContain(JAPAN);
    const offsets = choices.map((zone) => standardOffset(zone.key, 2026));
    expect(offsets).toEqual([...offsets].sort((a, b) => a - b));
    expect(choices[0].key).toBe("Pacific/Honolulu");
    expect(choices.at(-1)?.key).toBe("Pacific/Auckland");
  });

  it("labels each by its standard offset, whatever the season", () => {
    expect(offsetLabel(standardOffset(EASTERN, 2026))).toBe("UTC−05:00");
    expect(offsetLabel(standardOffset("Australia/Sydney", 2026))).toBe("UTC+10:00");
    expect(offsetLabel(standardOffset("Australia/Adelaide", 2026))).toBe("UTC+09:30");
    expect(offsetLabel(standardOffset("UTC", 2026))).toBe("UTC±00:00");
  });

  it("names the listed zones, and keeps a zone from before by its name", () => {
    expect(zoneName(EASTERN, "en")).toBe("US Eastern (ET)");
    expect(zoneName("Europe/Helsinki", "ja")).toBe("東ヨーロッパ時間（EET）");
    expect(zoneName("Europe/London", "en")).toBe("UK");
    expect(shortLabel("Europe/Berlin")).toBe("Berlin");
    expect(zoneName("Europe/Berlin", "en")).toBe("Europe/Berlin");
  });

  it("reads a listed zone typed after a time, and nothing else", () => {
    expect(zoneFromWord("ET")).toBe(EASTERN);
    expect(zoneFromWord("edt")).toBe(EASTERN);
    expect(zoneFromWord("london")).toBe("Europe/London");
    expect(zoneFromWord("CET")).toBe("Europe/Paris");
    expect(zoneFromWord("米国東部時間")).toBe(EASTERN);
    expect(zoneFromWord("Berlin")).toBeNull();
    expect(zoneFromWord("lots")).toBeNull();
  });
});

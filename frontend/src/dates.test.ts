import { describe, expect, it } from "vitest";

import { normaliseDate, parseClock, parseMoment } from "./dates";
import { convert, inOtherZones, zoneFromWord } from "./timeZones";

// 12 November 2026, the day Daniel asked for these.
const TODAY = new Date(2026, 10, 12);

describe("dates as people type them", () => {
  it.each([
    // Daniel's examples: this year's 26 is the year, wherever it stands.
    ["26/11/10", "2026-11-10"],
    ["26-11-10", "2026-11-10"],
    ["10/11/26", "2026-11-10"],
    ["10.11.26", "2026-11-10"],
    // Day before month, never US style when the day can be first.
    ["10/11/2026", "2026-11-10"],
    ["4/9/2026", "2026-09-04"],
    // ...but a US date that can't be read the other way is still understood.
    ["11/25/2026", "2026-11-25"],
    ["5/11/26", "2026-11-05"],
    ["26/11/5", "2026-11-05"],
    // Both ends could be a year near today: the reading closer to today.
    ["25/11/26", "2026-11-25"],
    ["26/11/25", "2026-11-25"],
    // Neither end near today: still the reading closer to today.
    ["10/11/12", "2012-11-10"],
    ["20261110", "2026-11-10"],
    ["26年11月10日", "2026-11-10"],
    ["2026年 11月 10日", "2026-11-10"],
    ["Nov 10, 2026", "2026-11-10"],
    ["November 10th 2026", "2026-11-10"],
    ["10th November 2026", "2026-11-10"],
  ])("reads %s as %s", (text, iso) => {
    expect(normaliseDate(text, TODAY)).toBe(iso);
  });

  it.each(["soon", "26/13/40", "1/2"])("passes %s on for the server to explain", (text) => {
    expect(normaliseDate(text, TODAY)).toBe(text);
  });
});

describe("times, perhaps with a zone", () => {
  it.each([
    ["10:00", { time: "10:00", zone: null }],
    ["  0:10", { time: "00:10", zone: null }],
    ["23:59:30", { time: "23:59:30", zone: null }],
    ["10:00 ET", { time: "10:00", zone: "America/New_York" }],
    ["10:00 EDT", { time: "10:00", zone: "America/New_York" }],
    ["2:30 pm JST", { time: "14:30", zone: "Asia/Tokyo" }],
    ["12am", { time: "00:00", zone: null }],
    ["1000 ET", { time: "10:00", zone: "America/New_York" }],
    ["14時10分", { time: "14:10", zone: null }],
    ["9:00 GMT", { time: "09:00", zone: "Europe/London" }],
  ])("reads %s", (text, clock) => {
    expect(parseClock(text, zoneFromWord)).toEqual(clock);
  });

  it.each(["soon", "9", "10:00 Mars", "13pm"])("does not read %s", (text) => {
    expect(parseClock(text, zoneFromWord)).toBeNull();
  });
});

describe("a date with a time, as an embargo notice gives it", () => {
  it.each([
    ["2026-11-10", { date: "2026-11-10", time: null, zone: null }],
    ["10 Nov 2026, 10:00 ET", { date: "2026-11-10", time: "10:00", zone: "America/New_York" }],
    ["2026/11/10 14:10", { date: "2026-11-10", time: "14:10", zone: null }],
    ["10/11/26 at 10:00 EST", { date: "2026-11-10", time: "10:00", zone: "America/New_York" }],
    ["2026-11-10 ET", { date: "2026-11-10", time: null, zone: "America/New_York" }],
  ])("reads %s", (text, moment) => {
    expect(parseMoment(text, zoneFromWord, TODAY)).toEqual(moment);
  });

  it("does not read a date it cannot read", () => {
    expect(parseMoment("someday 10:00", zoneFromWord, TODAY)).toBeNull();
  });
});

describe("time zones", () => {
  it("converts across midnight and summer time", () => {
    expect(convert("2026-11-10", "10:00", "America/New_York", "Asia/Tokyo")).toEqual({
      date: "2026-11-11",
      time: "00:00",
    });
    expect(convert("2026-08-14", "00:00", "Asia/Tokyo", "America/New_York")).toEqual({
      date: "2026-08-13",
      time: "11:00",
    });
  });

  it("shows a release time in the further zones, naming the date where it differs", () => {
    expect(
      inOtherZones("2026-11-10", "14:10:00", "Asia/Tokyo", ["America/New_York", "Europe/London"]),
    ).toEqual(["00:10 ET", "05:10 UK"]);
    expect(inOtherZones("2026-11-11", "00:00:00", "Asia/Tokyo", ["America/New_York"])).toEqual([
      "10:00 ET (2026-11-10)",
    ]);
    expect(inOtherZones("2026-11-11", null, "Asia/Tokyo", ["America/New_York"])).toEqual([]);
  });
});

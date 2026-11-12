import { describe, expect, it } from "vitest";

import { allZones, inOtherZones, shortLabel, zoneFromWord, zoneName } from "./timeZones";

describe("time zones beyond the listed seven (Daniel, 2026-11-12)", () => {
  it("names a listed zone as before, any other by its city", () => {
    expect(shortLabel("America/New_York")).toBe("ET");
    expect(shortLabel("Europe/Berlin")).toBe("Berlin");
    expect(shortLabel("Asia/Ho_Chi_Minh")).toBe("Ho Chi Minh");
    expect(zoneName("America/New_York", "en")).toBe("US Eastern (ET)");
    expect(zoneName("Europe/Berlin", "en")).toBe("Europe/Berlin (Central European Time)");
  });

  it("offers every zone the browser knows", () => {
    const zones = allZones();
    expect(zones).toContain("Europe/Berlin");
    expect(zones).toContain("UTC");
  });

  it("reads a city typed after a time as its zone", () => {
    expect(zoneFromWord("ET")).toBe("America/New_York");
    expect(zoneFromWord("Berlin")).toBe("Europe/Berlin");
    expect(zoneFromWord("europe/berlin")).toBe("Europe/Berlin");
    expect(zoneFromWord("sao paulo")).toBe("America/Sao_Paulo");
    expect(zoneFromWord("lots")).toBeNull();
  });

  it("shows a release time in each further zone, in the order chosen", () => {
    expect(
      inOtherZones("2026-11-10", "14:10:00", "Asia/Tokyo", ["Europe/Berlin", "America/New_York"]),
    ).toEqual(["06:10 Berlin", "00:10 ET"]);
  });
});

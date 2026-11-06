import { describe, expect, it } from "vitest";

import { formatDate, formatDateTime } from "./dates";

describe("dates", () => {
  it("show as YYYY-MM-DD whatever the language", () => {
    expect(formatDate("2026-04-01T03:00:00Z", "UTC")).toBe("2026-04-01");
  });

  it("use the institution's time zone, not the browser's or UTC", () => {
    // Late evening UTC is already the next day in Japan.
    expect(formatDate("2026-04-01T15:30:00Z", "Asia/Tokyo")).toBe("2026-04-02");
    expect(formatDateTime("2026-04-01T15:30:00Z", "Asia/Tokyo")).toBe("2026-04-02 00:30");
  });
});

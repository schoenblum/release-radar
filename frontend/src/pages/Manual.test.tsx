import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import i18n, { applyLanguage } from "../i18n";
import english from "../manual/en.md?raw";
import japanese from "../manual/ja.md?raw";
import Manual, { headingId, sections } from "./Manual";

describe("the Manual", () => {
  beforeEach(() => applyLanguage("en"));

  it("starts with the brief's everyday tasks, in both languages alike", () => {
    const en = sections(english);
    const ja = sections(japanese);
    // Step 1.9: short and task-oriented, the tasks first.
    expect(en.slice(0, 5).map((section) => section.title)).toEqual([
      "Add a release",
      "Fill in day-28 numbers",
      "Paste a column",
      "Set the release type",
      "Export for a report",
    ]);
    expect(en.map((section) => section.title)).toContain("Settings for admins");
    // The same sections, and the same subsections, in the same order.
    expect(ja).toHaveLength(en.length);
    const subsections = (text: string) => text.split("\n").filter((line) => line.startsWith("### "));
    expect(subsections(japanese)).toHaveLength(subsections(english).length);
    for (const list of [en, ja]) {
      expect(new Set(list.map((section) => section.id)).size).toBe(list.length);
    }
  });

  it("links each section from the contents", () => {
    render(<Manual />);
    const contents = screen.getByRole("navigation", { name: "On this page" });
    const link = within(contents).getByRole("link", { name: "Paste a column" });
    expect(link).toHaveAttribute("href", "#paste-a-column");
    expect(screen.getByRole("heading", { level: 2, name: "Paste a column" })).toHaveAttribute(
      "id",
      "paste-a-column",
    );
  });

  it("follows the language, with addresses for Japanese headings too", () => {
    applyLanguage("ja");
    render(<Manual />);
    const contents = screen.getByRole("navigation", { name: "このページの内容" });
    const link = within(contents).getByRole("link", { name: "列をまとめて貼り付ける" });
    expect(document.getElementById(link.getAttribute("href")!.slice(1))).toHaveTextContent(
      "列をまとめて貼り付ける",
    );
    expect(headingId("28 日目の数値を入力する")).toBe("28-日目の数値を入力する");
  });

  it("has the sections Settings links to, in both languages", () => {
    for (const [language, text] of [
      ["en", english],
      ["ja", japanese],
    ] as const) {
      const fixed = i18n.getFixedT(language);
      const titles = sections(text).map((section) => section.title);
      expect(titles).toContain(fixed("settings.integrations.ga4.manual_heading"));
      expect(titles).toContain(fixed("settings.profiles.manual_heading"));
    }
  });
});

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import type { Release } from "../../api/types";
import { ToastProvider } from "../../components/Toast";
import { applyLanguage } from "../../i18n";
import { buildColumns, type Commit } from "./columns";
import ReleaseGrid from "./ReleaseGrid";
import { context, measure, reading, release, UNIT } from "./testing";
import { useCellSaves } from "./useCellSaves";

const MEASURES = [
  measure("views.d0", { position: 0, label_en: "Views" }),
  measure("score.d0", { position: 1, unit: "score", label_en: "Score" }),
  measure("web.d28", { position: 2, source: "ga4", label_en: "Web" }),
];

function rows(count: number): Release[] {
  return Array.from({ length: count }, (_, index) => {
    const id = String(index + 1);
    return release(id, {
      unit_id: UNIT.id,
      readings: [
        reading("views.d0", { id: `${id}-views` }),
        reading("score.d0", { id: `${id}-score` }),
        reading("web.d28", { id: `${id}-web` }),
      ],
    });
  });
}

type Apply = (releaseId: string, commit: Commit, version?: number) => Promise<void>;

function Harness({
  apply,
  onOpen,
  canEdit = true,
  initial,
}: {
  apply: Apply;
  onOpen: (id: string) => void;
  canEdit?: boolean;
  initial: Release[];
}) {
  const [list] = useState(initial);
  const saves = useCellSaves(apply);
  const columns = buildColumns(context({ measures: MEASURES, canEdit }));
  return (
    <ReleaseGrid
      rows={list}
      allColumns={columns}
      choice={{ hidden: [], shown: [] }}
      canEdit={canEdit}
      saves={saves}
      units={[UNIT]}
      newRow={null}
      empty="Nothing here"
      onOpen={onOpen}
      onRefresh={() => undefined}
    />
  );
}

function setup(options: { apply?: Apply; canEdit?: boolean; initial?: Release[] } = {}) {
  const apply = vi.fn<Apply>(options.apply ?? (async () => undefined));
  const onOpen = vi.fn<(id: string) => void>();
  render(
    <ToastProvider>
      <Harness
        apply={apply}
        onOpen={onOpen}
        canEdit={options.canEdit ?? true}
        initial={options.initial ?? rows(6)}
      />
    </ToastProvider>,
  );
  return { apply, onOpen, user: userEvent.setup() };
}

const cell = (rowId: string, column: string): HTMLElement => {
  const found = document.getElementById(`cell-${rowId}-${column}`);
  if (!found) throw new Error(`No cell ${rowId} ${column}`);
  return found;
};
const VIEWS = "measure:views.d0";
const SCORE = "measure:score.d0";

function paste(text: string): void {
  fireEvent.paste(screen.getByRole("grid"), {
    clipboardData: { getData: () => text },
  });
}

describe("the data grid", () => {
  beforeAll(() => {
    // jsdom lays nothing out. The grid needs room to show its rows.
    Object.defineProperty(Element.prototype, "clientHeight", { configurable: true, value: 600 });
    Object.defineProperty(Element.prototype, "clientWidth", { configurable: true, value: 2000 });
    Element.prototype.scrollIntoView = vi.fn();
  });

  beforeEach(() => applyLanguage("en"));
  afterEach(() => vi.restoreAllMocks());

  it("selects a cell on click, and moves with the arrow keys", async () => {
    const { user } = setup();
    await user.click(cell("1", VIEWS));
    expect(cell("1", VIEWS)).toHaveClass("is-active");
    expect(screen.getByRole("grid")).toHaveFocus();
    await user.keyboard("{ArrowDown}{ArrowRight}");
    expect(cell("2", SCORE)).toHaveClass("is-active");
    expect(cell("1", VIEWS)).not.toHaveClass("is-active");
    await user.keyboard("{ArrowUp}{ArrowLeft}");
    expect(cell("1", VIEWS)).toHaveClass("is-active");
  });

  it("starts at the first cell when reached by Tab", async () => {
    const { user } = setup();
    await user.tab();
    expect(cell("1", "code")).toHaveClass("is-active");
  });

  it("typing replaces the cell, Enter saves and moves down", async () => {
    const { apply, user } = setup();
    await user.click(cell("1", VIEWS));
    await user.keyboard("1,234{Enter}");
    expect(apply).toHaveBeenCalledWith(
      "1",
      { kind: "reading", readingId: "1-views", body: { value: "1,234" } },
      undefined,
    );
    expect(cell("2", VIEWS)).toHaveClass("is-active");
    expect(screen.getByRole("grid")).toHaveFocus();
  });

  it("keeps every character of fast typing", async () => {
    const { apply, user } = setup();
    await user.click(cell("1", VIEWS));
    await user.keyboard("{1}{2}{3}{4}{5}{Enter}");
    expect(apply.mock.calls[0][1]).toMatchObject({ body: { value: "12345" } });
  });

  it("Tab saves and moves right, and Shift+Tab goes back", async () => {
    const { apply, user } = setup();
    await user.click(cell("1", VIEWS));
    await user.keyboard("5{Tab}");
    expect(apply).toHaveBeenCalledTimes(1);
    expect(cell("1", SCORE)).toHaveClass("is-active");
    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(cell("1", VIEWS)).toHaveClass("is-active");
  });

  it("Esc gives up an edit and saves nothing", async () => {
    const { apply, user } = setup();
    await user.click(cell("1", VIEWS));
    await user.keyboard("99{Escape}");
    expect(apply).not.toHaveBeenCalled();
    expect(within(cell("1", VIEWS)).queryByRole("textbox")).toBeNull();
    expect(screen.getByRole("grid")).toHaveFocus();
  });

  it("Enter changes what is there rather than replacing it", async () => {
    const { apply, user } = setup();
    await user.click(cell("1", "title"));
    await user.keyboard("{Enter}");
    expect(within(cell("1", "title")).getByRole("textbox")).toHaveValue("Release 1");
    await user.keyboard(" more{Enter}");
    expect(apply.mock.calls[0][1]).toEqual({ kind: "field", field: "title", value: "Release 1 more" });
  });

  it("saves nothing when nothing changed", async () => {
    const { apply, user } = setup();
    await user.click(cell("1", "title"));
    await user.keyboard("{Enter}{Enter}");
    expect(apply).not.toHaveBeenCalled();
    expect(cell("2", "title")).toHaveClass("is-active");
  });

  it("saving by clicking elsewhere works too", async () => {
    const { apply, user } = setup();
    await user.click(cell("1", VIEWS));
    await user.keyboard("7");
    await user.click(cell("3", SCORE));
    expect(apply).toHaveBeenCalledTimes(1);
    expect(apply.mock.calls[0][1]).toMatchObject({ body: { value: "7" } });
    expect(cell("3", SCORE)).toHaveClass("is-active");
  });

  it("does not type into what cannot be changed", async () => {
    const { apply, user } = setup();
    await user.click(cell("1", "measure:web.d28"));
    await user.keyboard("5");
    expect(within(cell("1", "measure:web.d28")).queryByRole("textbox")).toBeNull();
    expect(apply).not.toHaveBeenCalled();
  });

  it("a failed save stays on screen, with the reason, and blocks nothing else", async () => {
    const apply: Apply = async (_, commit) => {
      if (commit.kind === "reading" && "value" in commit.body && commit.body.value === "abc") {
        throw new ApiError(422, "field_invalid");
      }
    };
    const { user } = setup({ apply });
    await user.click(cell("1", VIEWS));
    await user.keyboard("abc{Tab}");
    await waitFor(() => expect(cell("1", VIEWS)).toHaveClass("is-failed"));
    expect(cell("1", VIEWS)).toHaveTextContent("abc");

    // The next cell works as usual.
    await user.keyboard("5{Enter}");
    await waitFor(() => expect(cell("1", SCORE)).toHaveClass("is-saved"));

    // Selecting the cell explains, Enter reopens what was typed, and Esc drops it.
    await user.click(cell("1", VIEWS));
    expect(within(cell("1", VIEWS)).getByRole("alert")).toHaveTextContent("Please enter a number");
    await user.keyboard("{Enter}");
    expect(within(cell("1", VIEWS)).getByRole("textbox")).toHaveValue("abc");
    await user.keyboard("{Escape}{Escape}");
    expect(cell("1", VIEWS)).not.toHaveClass("is-failed");
    expect(cell("1", VIEWS)).toHaveTextContent("");
  });

  it("offers a choice when someone else changed the same cell", async () => {
    let calls = 0;
    const apply: Apply = async () => {
      calls += 1;
      if (calls === 1) {
        throw new ApiError(409, "conflict", {
          current_value: 777,
          current_version: 4,
          current_state: "value",
        });
      }
    };
    const { user } = setup({ apply });
    await user.click(cell("1", VIEWS));
    await user.keyboard("5{Enter}{ArrowUp}");
    const message = await within(cell("1", VIEWS)).findByRole("alert");
    expect(message).toHaveTextContent("777");
    await user.click(within(message).getByRole("button", { name: "Keep mine" }));
    await waitFor(() => expect(cell("1", VIEWS)).not.toHaveClass("is-failed"));
    expect(calls).toBe(2);
  });

  it("Delete clears the selected range", async () => {
    const { apply, user } = setup();
    await user.click(cell("1", VIEWS));
    await user.keyboard("{Shift>}{ArrowDown}{/Shift}{Delete}");
    expect(apply.mock.calls.map((call) => call[0])).toEqual(["1", "2"]);
    expect(apply.mock.calls[0][1]).toMatchObject({ body: { state: "missing" } });
  });

  it("Shift and the arrows select a range, and a plain arrow collapses it", async () => {
    const { user } = setup();
    await user.click(cell("1", VIEWS));
    await user.keyboard("{Shift>}{ArrowDown}{ArrowRight}{/Shift}");
    for (const [row, column] of [
      ["1", VIEWS],
      ["1", SCORE],
      ["2", VIEWS],
      ["2", SCORE],
    ]) {
      expect(cell(row, column)).toHaveClass("in-range");
    }
    expect(cell("3", VIEWS)).not.toHaveClass("in-range");
    await user.keyboard("{ArrowDown}");
    expect(cell("1", VIEWS)).not.toHaveClass("in-range");
    expect(cell("3", SCORE)).toHaveClass("in-range");
  });

  it("pastes a column from the selected cell, and says how it went", async () => {
    const apply: Apply = async (_, commit) => {
      if (commit.kind === "reading" && "value" in commit.body && commit.body.value === "bad") {
        throw new ApiError(422, "field_invalid");
      }
    };
    const { user } = setup({ apply });
    await user.click(cell("1", VIEWS));
    paste("12\n1,500\nbad\n-\n");
    expect(await screen.findByText(/3 saved, 1 invalid/)).toBeInTheDocument();
    expect(cell("3", VIEWS)).toHaveClass("is-failed");
    expect(cell("3", VIEWS)).toHaveTextContent("bad");
    expect(screen.getByRole("button", { name: "Undo" })).toBeInTheDocument();
  });

  it("holds the focus somewhere editable while Cmd or Ctrl is down, for Safari's clipboard", async () => {
    const { user } = setup();
    await user.click(cell("1", VIEWS));
    await user.keyboard("{Meta>}");
    const catcher = document.querySelector("textarea");
    expect(catcher).toHaveFocus();
    expect(catcher).not.toHaveAttribute("readonly");
    fireEvent.paste(catcher as HTMLElement, { clipboardData: { getData: () => "12" } });
    expect(await screen.findByText(/1 saved/)).toBeInTheDocument();
    await user.keyboard("{/Meta}");
    expect(screen.getByRole("grid")).toHaveFocus();
  });

  it("does not paste for a viewer", async () => {
    const { apply, user } = setup({ canEdit: false });
    await user.click(cell("1", VIEWS));
    paste("12");
    expect(apply).not.toHaveBeenCalled();
  });

  it("copies the selected range the way a spreadsheet reads it", async () => {
    const { user } = setup();
    await user.click(cell("1", "code"));
    await user.keyboard("{Shift>}{ArrowDown}{ArrowRight}{/Shift}");
    const setData = vi.fn();
    fireEvent.copy(screen.getByRole("grid"), { clipboardData: { setData } });
    expect(setData).toHaveBeenCalledWith(
      "text/plain",
      "AY2026-1\tRelease 1\nAY2026-2\tRelease 2",
    );
  });

  it("Cmd+Z undoes the last edit", async () => {
    const before = rows(1);
    before[0].readings[0] = reading("views.d0", {
      id: "1-views",
      value: 10,
      state: "value",
      display_state: "value",
    });
    const { apply, user } = setup({ initial: before });
    await user.click(cell("1", VIEWS));
    await user.keyboard("20{Enter}");
    await waitFor(() => expect(apply).toHaveBeenCalledTimes(1));
    await user.keyboard("{Meta>}z{/Meta}");
    await waitFor(() => expect(apply).toHaveBeenCalledTimes(2));
    expect(apply.mock.calls[1][1]).toMatchObject({ body: { value: 10 } });
    expect(await screen.findByText(/Undone: 1/)).toBeInTheDocument();
  });

  it("undoes a whole paste in one go, and with nothing left does nothing", async () => {
    const { apply, user } = setup();
    await user.click(cell("1", VIEWS));
    paste("1\n2");
    await waitFor(() => expect(apply).toHaveBeenCalledTimes(2));
    await screen.findByText(/2 saved/);
    await user.keyboard("{Control>}z{/Control}");
    await waitFor(() => expect(apply).toHaveBeenCalledTimes(4));
    await user.keyboard("{Control>}z{/Control}");
    expect(apply).toHaveBeenCalledTimes(4);
  });

  it("a click on a title, or Shift+Enter anywhere, opens the full record", async () => {
    const { onOpen, user } = setup();
    await user.click(within(cell("2", "title")).getByRole("button"));
    expect(onOpen).toHaveBeenCalledWith("2");
    await user.click(cell("3", VIEWS));
    await user.keyboard("{Shift>}{Enter}{/Shift}");
    expect(onOpen).toHaveBeenLastCalledWith("3");
  });

  it("a box toggles with one click or the space bar", async () => {
    const { apply, user } = setup();
    await user.click(within(cell("1", "ea_top_page")).getByRole("checkbox"));
    expect(apply.mock.calls[0][1]).toEqual({ kind: "field", field: "ea_top_page", value: true });
    await user.click(cell("2", "ea_top_page"));
    await user.keyboard(" ");
    expect(apply.mock.calls[1][0]).toBe("2");
  });

  it("a choice opens as a list, and saves what was picked", async () => {
    const { apply, user } = setup();
    await user.click(cell("1", "unit"));
    await user.keyboard("{Enter}");
    const select = within(cell("1", "unit")).getByRole("combobox");
    expect(select).toHaveValue("School of Science");
    await user.selectOptions(select, "None");
    await user.keyboard("{Enter}");
    expect(apply.mock.calls[0][1]).toEqual({ kind: "field", field: "unit_id", value: null });
  });

  it("a viewer can look around but change nothing", async () => {
    const { apply, user } = setup({ canEdit: false });
    await user.click(cell("1", VIEWS));
    await user.keyboard("5{Enter}{Delete}");
    expect(apply).not.toHaveBeenCalled();
    expect(within(cell("1", "ea_top_page")).getByRole("checkbox")).toBeDisabled();
  });

  it("describes itself to assistive technology", async () => {
    const { user } = setup();
    const grid = screen.getByRole("grid");
    expect(grid).toHaveAttribute("aria-rowcount", "7");
    await user.click(cell("2", VIEWS));
    expect(grid).toHaveAttribute("aria-activedescendant", cell("2", VIEWS).id);
    expect(cell("2", VIEWS)).toHaveAttribute("aria-selected", "true");
    expect(cell("2", "code")).toHaveAttribute("aria-readonly", "true");
  });

  it("says so when empty", () => {
    setup({ initial: [] });
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });
});

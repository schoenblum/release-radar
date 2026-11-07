import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import type { CrossrefStatus, ReleaseCreated } from "../../api/types";
import { ToastProvider } from "../../components/Toast";
import { applyLanguage } from "../../i18n";
import NewReleaseRow from "./NewReleaseRow";
import { release } from "./testing";

function created(status: CrossrefStatus | null): ReleaseCreated {
  return { ...release("1", { paper_title: "A paper" }), crossref: status };
}

function setup(create = vi.fn(async () => created(null))) {
  const onLeaveDown = vi.fn();
  render(
    <ToastProvider>
      <NewReleaseRow create={create} onLeaveDown={onLeaveDown} />
    </ToastProvider>,
  );
  return { create, onLeaveDown, user: userEvent.setup(), input: screen.getByRole("textbox") };
}

describe("the new-release row", () => {
  beforeEach(() => applyLanguage("en"));

  it("takes a title, then stays ready for the next one", async () => {
    const { create, input, user } = setup();
    await user.click(input);
    await user.keyboard("Bees navigate{Enter}");
    expect(create).toHaveBeenCalledWith({ title: "Bees navigate" });
    await waitFor(() => expect(input).toHaveValue(""));
    expect(input).toHaveFocus();
    await user.keyboard("Next one{Enter}");
    expect(create).toHaveBeenLastCalledWith({ title: "Next one" });
  });

  it("recognises a DOI", async () => {
    const { create, input, user } = setup();
    await user.click(input);
    await user.keyboard("https://doi.org/10.1038/x{Enter}");
    expect(create).toHaveBeenCalledWith({ doi: "https://doi.org/10.1038/x" });
  });

  it("does nothing with nothing typed", async () => {
    const { create, input, user } = setup();
    await user.click(input);
    await user.keyboard("   {Enter}");
    expect(create).not.toHaveBeenCalled();
  });

  it.each([
    ["found", /Found the paper: A paper/],
    ["not_found", /doesn't know this DOI/],
    ["unavailable", /can't be reached/],
  ] as const)("says what Crossref answered: %s", async (status, message) => {
    const { input, user } = setup(vi.fn(async () => created(status)));
    await user.click(input);
    await user.keyboard("10.1038/x{Enter}");
    expect(await screen.findByText(message)).toBeInTheDocument();
  });

  it("keeps what was typed if it cannot be saved, with the reason", async () => {
    const { input, user } = setup(
      vi.fn(async () => {
        throw new ApiError(422, "invalid_doi");
      }),
    );
    await user.click(input);
    await user.keyboard("10.1/x{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent("DOI");
    expect(input).toHaveValue("10.1/x");
  });

  it("the down arrow moves into the grid", async () => {
    const { onLeaveDown, input, user } = setup();
    await user.click(input);
    await user.keyboard("{ArrowDown}");
    expect(onLeaveDown).toHaveBeenCalled();
  });
});

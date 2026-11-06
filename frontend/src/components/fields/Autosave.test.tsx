import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import { applyLanguage } from "../../i18n";
import { decodeCsv } from "../CsvTools";
import { parseOptions } from "../CustomFieldEditor";
import { SelectField, TextField, ToggleField } from "./Autosave";

const conflict = new ApiError(409, "conflict", {
  detail: "conflict",
  current_value: "Theirs",
  current_version: 4,
});

describe("autosaving fields", () => {
  beforeEach(() => applyLanguage("en"));

  it("saves when the person leaves the field, naming the version it last saw", async () => {
    const save = vi.fn().mockResolvedValue({ value: "New", version: 3 });
    const user = userEvent.setup();
    render(<TextField label="Name" value="Old" version={2} save={save} />);

    await user.clear(screen.getByRole("textbox", { name: "Name" }));
    await user.type(screen.getByRole("textbox", { name: "Name" }), "New");
    await user.tab();

    expect(save).toHaveBeenCalledExactlyOnceWith("New", 2);
    expect(await screen.findByText("Saved")).toBeInTheDocument();
  });

  it("saves on Enter, and a second save uses the newer version straight away", async () => {
    const save = vi
      .fn()
      .mockResolvedValueOnce({ value: "One", version: 1 })
      .mockResolvedValueOnce({ value: "Two", version: 2 });
    const user = userEvent.setup();
    render(<TextField label="Name" value="" version={0} save={save} />);
    const input = screen.getByRole("textbox", { name: "Name" });

    await user.type(input, "One{Enter}");
    await screen.findByText("Saved");
    await user.clear(input);
    await user.type(input, "Two{Enter}");

    expect(save).toHaveBeenLastCalledWith("Two", 1);
  });

  it("does not save when nothing changed", async () => {
    const save = vi.fn();
    const user = userEvent.setup();
    render(<TextField label="Name" value="Same" save={save} />);
    await user.click(screen.getByRole("textbox", { name: "Name" }));
    await user.tab();
    expect(save).not.toHaveBeenCalled();
  });

  it("goes back on Esc without saving", async () => {
    const save = vi.fn();
    const user = userEvent.setup();
    render(<TextField label="Name" value="Old" save={save} />);
    const input = screen.getByRole("textbox", { name: "Name" });
    await user.type(input, " changed{Escape}");
    expect(input).toHaveValue("Old");
    await user.tab();
    expect(save).not.toHaveBeenCalled();
  });

  it("keeps invalid input on screen and explains it in plain language", async () => {
    const save = vi.fn().mockRejectedValue(new ApiError(422, "field_required"));
    const user = userEvent.setup();
    render(<TextField label="Name" value="Old" save={save} />);
    const input = screen.getByRole("textbox", { name: "Name" });
    await user.clear(input);
    await user.tab();

    expect(await screen.findByRole("alert")).toHaveTextContent("This can't be empty.");
    expect(input).toHaveValue("");
    expect(input).toHaveAttribute("aria-invalid", "true");
  });

  it("shows the current value on a conflict, and can keep mine", async () => {
    const save = vi
      .fn()
      .mockRejectedValueOnce(conflict)
      .mockResolvedValueOnce({ value: "Mine", version: 5 });
    const user = userEvent.setup();
    render(<TextField label="Name" value="Old" version={3} save={save} />);
    const input = screen.getByRole("textbox", { name: "Name" });
    await user.clear(input);
    await user.type(input, "Mine{Enter}");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Someone else just changed this to “Theirs”.",
    );
    await user.click(screen.getByRole("button", { name: "Keep mine" }));

    expect(save).toHaveBeenLastCalledWith("Mine", 4);
    expect(await screen.findByText("Saved")).toBeInTheDocument();
    expect(input).toHaveValue("Mine");
  });

  it("can use theirs on a conflict, and the next save uses their version", async () => {
    const save = vi
      .fn()
      .mockRejectedValueOnce(conflict)
      .mockResolvedValueOnce({ value: "Theirs edited", version: 5 });
    const user = userEvent.setup();
    render(<TextField label="Name" value="Old" version={3} save={save} />);
    const input = screen.getByRole("textbox", { name: "Name" });
    await user.clear(input);
    await user.type(input, "Mine{Enter}");
    await user.click(await screen.findByRole("button", { name: "Use theirs" }));

    expect(input).toHaveValue("Theirs");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    await user.type(input, " edited{Enter}");
    expect(save).toHaveBeenLastCalledWith("Theirs edited", 4);
  });

  it("takes a value from a refetch, unless the person is typing", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<TextField label="Name" value="One" save={vi.fn()} />);
    rerender(<TextField label="Name" value="Two" save={vi.fn()} />);
    const input = screen.getByRole("textbox", { name: "Name" });
    expect(input).toHaveValue("Two");

    await user.type(input, " typing");
    rerender(<TextField label="Name" value="Three" save={vi.fn()} />);
    expect(input).toHaveValue("Two typing");
  });

  it("shows what the server tidied", async () => {
    const save = vi.fn().mockResolvedValue({ value: "news.example.org", version: 1 });
    const user = userEvent.setup();
    render(<TextField label="Domain" value="" save={save} />);
    const input = screen.getByRole("textbox", { name: "Domain" });
    await user.type(input, "HTTPS://News.Example.org/{Enter}");
    await screen.findByText("Saved");
    expect(input).toHaveValue("news.example.org");
  });

  it("saves a choice as soon as it is made", async () => {
    const save = vi.fn().mockResolvedValue({ value: "b", version: 1 });
    const user = userEvent.setup();
    render(
      <SelectField
        label="Pick"
        value="a"
        save={save}
        options={[
          { value: "a", label: "A" },
          { value: "b", label: "B" },
        ]}
      />,
    );
    await user.selectOptions(screen.getByRole("combobox", { name: "Pick" }), "b");
    expect(save).toHaveBeenCalledExactlyOnceWith("b", 0);
  });

  it("saves a checkbox as soon as it is clicked", async () => {
    const save = vi.fn().mockResolvedValue({ value: false, version: 1 });
    const user = userEvent.setup();
    render(<ToggleField label="Active" value={true} save={save} />);
    await user.click(screen.getByRole("checkbox", { name: "Active" }));
    expect(save).toHaveBeenCalledExactlyOnceWith(false, 0);
  });

  it("explains conflicts in Japanese too", async () => {
    applyLanguage("ja");
    const save = vi.fn().mockRejectedValueOnce(conflict);
    const user = userEvent.setup();
    render(<TextField label="名前" value="Old" save={save} />);
    await user.type(screen.getByRole("textbox", { name: "名前" }), "!{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent("「Theirs」に変更しました");
  });
});

describe("csv files", () => {
  it("reads UTF-8", () => {
    expect(decodeCsv(new TextEncoder().encode("研究科").buffer as ArrayBuffer)).toBe("研究科");
  });

  it("falls back to Shift-JIS, which Japanese Excel saves by default", () => {
    // 研究 in Shift-JIS.
    const bytes = new Uint8Array([0x8c, 0xa4, 0x8b, 0x86]);
    expect(decodeCsv(bytes.buffer as ArrayBuffer)).toBe("研究");
  });
});

describe("choices written on a custom field", () => {
  it("reads English and Japanese from each line and ignores blanks", () => {
    expect(parseOptions("Newspaper | 新聞\n\n  Radio  \n")).toEqual([
      { label_en: "Newspaper", label_ja: "新聞" },
      { label_en: "Radio", label_ja: null },
    ]);
  });
});

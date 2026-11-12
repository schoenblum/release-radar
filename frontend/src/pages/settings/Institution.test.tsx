import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Institution } from "../../api/types";
import { applyLanguage } from "../../i18n";
import { DisplayZones } from "./Institution";

function institution(zones: (string | null)[]): Institution {
  return {
    timezone: "Asia/Tokyo",
    display_time_zones: zones,
    field_versions: { display_time_zones: 4 },
  } as unknown as Institution;
}

describe("the further zones a release time shows in", () => {
  beforeEach(() => applyLanguage("en"));

  it("offers three places, any zone in each, and none", async () => {
    const save = vi.fn().mockResolvedValue({});
    render(<DisplayZones institution={institution(["America/New_York"])} save={save} />);
    const places = ["Zone 1", "Zone 2", "Zone 3"].map((name) =>
      screen.getByRole("combobox", { name }),
    );
    expect(places.map((place) => (place as HTMLSelectElement).value)).toEqual([
      "America/New_York",
      "",
      "",
    ]);
    // A list of time zones by standard offset, not every city; never the institution's own.
    const options = within(places[1]).getAllByRole("option");
    expect(options[0]).toHaveTextContent("None");
    expect(options[1]).toHaveTextContent("UTC−10:00 Hawaii (HT)");
    expect(options.length).toBeLessThan(40);
    expect(within(places[1]).queryByRole("option", { name: /Japan/ })).toBeNull();
    expect(
      within(places[1]).getByRole("option", { name: "UTC+02:00 Eastern Europe (EET)" }),
    ).toBeInTheDocument();

    await userEvent.selectOptions(places[1], "Europe/Helsinki");
    expect(save).toHaveBeenLastCalledWith(["America/New_York", "Europe/Helsinki", null], 4);
    await userEvent.selectOptions(places[0], "");
    expect(save).toHaveBeenLastCalledWith([null, null, null], 4);
  });

  it("moves a zone chosen again to its new place", async () => {
    const save = vi.fn().mockResolvedValue({});
    render(
      <DisplayZones
        institution={institution(["America/New_York", "Europe/London"])}
        save={save}
      />,
    );
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Zone 3" }), "America/New_York");
    expect(save).toHaveBeenLastCalledWith([null, "Europe/London", "America/New_York"], 4);
  });
});

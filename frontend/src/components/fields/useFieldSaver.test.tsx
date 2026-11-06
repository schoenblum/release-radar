import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { http } from "../../api/client";
import { useFieldSaver } from "./useFieldSaver";

describe("saving one field", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("refreshes every listed query, so a new name or timezone shows without a reload", async () => {
    const patch = vi
      .spyOn(http, "patchField")
      .mockResolvedValue({ field: "timezone", value: "Asia/Seoul", version: 2 });
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(
      () => useFieldSaver("/settings/institution", ["settings"], ["brand"]),
      { wrapper },
    );

    await result.current("timezone")("Asia/Seoul", 1);

    expect(patch).toHaveBeenCalledExactlyOnceWith(
      "/settings/institution",
      "timezone",
      "Asia/Seoul",
      1,
    );
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["settings"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["brand"] });
  });
});

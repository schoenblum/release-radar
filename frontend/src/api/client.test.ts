import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError, onSessionLost, setAccessToken } from "./client";

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const user = { id: "1", email: "someone@example.org", role: "editor" };

describe("api client", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    setAccessToken("expired");
    onSessionLost(() => undefined);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("refreshes the session once after a 401 and retries with the new token", async () => {
    fetchMock
      .mockResolvedValueOnce(json(401, { detail: "invalid_token" }))
      .mockResolvedValueOnce(json(200, { access_token: "fresh", user }))
      .mockResolvedValueOnce(json(200, { ...user, language: "ja" }));

    const result = await api.updateMe({ language: "ja" });

    expect(result.language).toBe("ja");
    expect(fetchMock).toHaveBeenCalledTimes(3);
    const retry = fetchMock.mock.calls[2][1];
    expect(new Headers(retry?.headers).get("Authorization")).toBe("Bearer fresh");
  });

  it("shares one refresh between requests that fail together", async () => {
    let refreshes = 0;
    fetchMock.mockImplementation(async (input, init) => {
      if (String(input).endsWith("/auth/refresh")) {
        refreshes += 1;
        return json(200, { access_token: "fresh", user });
      }
      const authorization = new Headers(init?.headers).get("Authorization");
      return authorization === "Bearer fresh"
        ? json(200, user)
        : json(401, { detail: "invalid_token" });
    });

    await Promise.all([api.updateMe({ language: "ja" }), api.updateMe({ language: "en" })]);

    expect(refreshes).toBe(1);
  });

  it("reports a lost session when the refresh is refused", async () => {
    const lost = vi.fn();
    onSessionLost(lost);
    fetchMock
      .mockResolvedValueOnce(json(401, { detail: "invalid_token" }))
      .mockResolvedValueOnce(json(401, { detail: "session_expired" }));

    await expect(api.updateMe({ language: "ja" })).rejects.toMatchObject({
      code: "session_expired",
    });
    expect(lost).toHaveBeenCalledOnce();
  });

  it("stays signed in when the refresh fails because of the network", async () => {
    const lost = vi.fn();
    onSessionLost(lost);
    fetchMock
      .mockResolvedValueOnce(json(401, { detail: "invalid_token" }))
      .mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(api.updateMe({ language: "ja" })).rejects.toBeInstanceOf(TypeError);
    expect(lost).not.toHaveBeenCalled();
  });

  it("does not try to refresh after a failed sign-in", async () => {
    fetchMock.mockResolvedValueOnce(json(401, { detail: "invalid_credentials" }));

    const failure = await api.login("someone@example.org", "wrong").catch((error) => error);

    expect(failure).toBeInstanceOf(ApiError);
    expect(failure.code).toBe("invalid_credentials");
    expect(fetchMock).toHaveBeenCalledOnce();
  });
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Ga4Status } from "../../api/types";
import { ToastProvider } from "../../components/Toast";
import { applyLanguage } from "../../i18n";
import IntegrationsSettings from "./Integrations";

vi.mock("../../brand", () => ({
  useBrand: () => ({ timezone: "Asia/Tokyo" }),
}));

const EMPTY: Ga4Status = {
  configured: false,
  readable: false,
  client_email: null,
  project_id: null,
  property_id: null,
  field_versions: {},
  domain: "news.example.org",
  first_fetch_at: null,
  last_test_at: null,
  last_test: null,
  last_run: null,
  running: false,
  fetched: 0,
  waiting: [],
  not_yet_due: 0,
};

const CONNECTED: Ga4Status = {
  ...EMPTY,
  configured: true,
  readable: true,
  client_email: "reader@example-project.example.org",
  project_id: "example-project",
  property_id: "123456789",
  field_versions: { property_id: 1 },
  waiting: [
    {
      release_id: "r1",
      code: "AY2026-07",
      title: "A synthetic release",
      website_url: "https://news.example.org/news/a-synthetic-release/",
      release_date: "2026-09-01",
    },
  ],
  not_yet_due: 3,
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function setup(initial: Ga4Status, answers: Record<string, () => Response> = {}) {
  let status = initial;
  const sent: { method: string; url: string; body: unknown }[] = [];
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    sent.push({
      method,
      url,
      body: init?.body ? JSON.parse(String(init.body)) : undefined,
    });
    const answer = answers[`${method} ${url.replace("/api/v1", "")}`];
    if (answer) return answer();
    if (method === "PUT") {
      status = {
        ...CONNECTED,
        property_id: null,
        field_versions: {},
        waiting: [],
      };
      return json(status);
    }
    return json(status);
  });
  vi.stubGlobal("fetch", fetchMock);
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <ToastProvider>
        <MemoryRouter>
          <IntegrationsSettings />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
  return { user: userEvent.setup(), sent };
}

describe("Settings → Integrations", () => {
  beforeEach(() => applyLanguage("en"));
  afterEach(() => vi.unstubAllGlobals());

  it("takes the key file and sends its text, never showing it", async () => {
    const { user, sent } = setup(EMPTY);
    await screen.findByText("Not connected yet.");
    expect(screen.getByRole("button", { name: "Test connection" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Fetch now" })).toBeDisabled();

    const file = new File(['{"type": "synthetic"}'], "release-radar-key.json", {
      type: "application/json",
    });
    await user.upload(screen.getByLabelText("Service-account key (JSON file)"), file);

    await screen.findByText(
      "Key stored for reader@example-project.example.org (Google Cloud project example-project).",
    );
    const put = sent.find((request) => request.method === "PUT");
    expect(put?.url).toBe("/api/v1/integrations/ga4/key");
    expect(put?.body).toEqual({ key: '{"type": "synthetic"}' });
    // Without a property ID there is still nothing to test.
    expect(screen.getByRole("button", { name: "Test connection" })).toBeDisabled();
  });

  it("explains a file that is not a key", async () => {
    const { user } = setup(EMPTY, {
      "PUT /integrations/ga4/key": () => json({ detail: "ga4_key_not_service_account" }, 422),
    });
    await screen.findByText("Not connected yet.");
    await user.upload(
      screen.getByLabelText("Service-account key (JSON file)"),
      new File(["{}"], "something.json", { type: "application/json" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "That file isn't a service-account key.",
    );
  });

  it("tests the connection and says what it found", async () => {
    const { user } = setup(CONNECTED, {
      "POST /integrations/ga4/test": () =>
        json({
          ok: false,
          code: "no_access",
          detail: null,
          date: "2026-11-08",
          host: "news.example.org",
        }),
    });
    await user.click(await screen.findByRole("button", { name: "Test connection" }));
    expect(
      await screen.findByText(/The service account has no access to this property/),
    ).toBeInTheDocument();
  });

  it("reports a successful test with the day's views", async () => {
    const { user } = setup(CONNECTED, {
      "POST /integrations/ga4/test": () =>
        json({
          ok: true,
          code: "connected",
          detail: null,
          views: 1234,
          date: "2026-11-08",
          host: "news.example.org",
        }),
    });
    await user.click(await screen.findByRole("button", { name: "Test connection" }));
    expect(
      await screen.findByText(
        "Connected. Google Analytics counted 1,234 page views on news.example.org on 2026-11-08.",
      ),
    ).toBeInTheDocument();
  });

  it("starts a fetch, and lists what is still waiting with a link to its record", async () => {
    const { user, sent } = setup(CONNECTED, {
      "POST /integrations/ga4/fetch": () => json({ started: true }, 202),
    });
    expect(
      await screen.findByText(
        "Daily fetches start after the first Fetch now. The first one fetches every release since the new website went live.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "0 with website views from Google Analytics, 1 still waiting, 3 within their 28 days.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "A synthetic release" })).toHaveAttribute(
      "href",
      "/data?view=all&release=r1",
    );
    expect(screen.getByRole("link", { name: "/news/a-synthetic-release/" })).toHaveAttribute(
      "target",
      "_blank",
    );
    await user.click(screen.getByRole("button", { name: "Fetch now" }));
    await waitFor(() =>
      expect(
        sent.some((request) => request.method === "POST" && request.url.endsWith("/fetch")),
      ).toBe(true),
    );
    expect(await screen.findByText(/Fetching website views/)).toBeInTheDocument();
  });

  it("says when a stored key cannot be read here", async () => {
    setup({ ...CONNECTED, readable: false });
    expect(
      await screen.findByText("The stored key cannot be read on this install; enter it again."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Fetch now" })).toBeDisabled();
  });

  it("links to the Manual's steps in the page's language", async () => {
    applyLanguage("ja");
    setup(EMPTY);
    expect(await screen.findByRole("link", { name: "接続の手順" })).toHaveAttribute(
      "href",
      "/manual#google-analytics-に接続する",
    );
  });
});

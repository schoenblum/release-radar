import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { lazy, Suspense } from "react";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { applyLanguage } from "../i18n";
import Layout from "./Layout";

vi.mock("../auth", () => ({
  useAuth: () => ({ user: { role: "viewer", email: "viewer@example.org" }, logout: vi.fn() }),
}));
vi.mock("../brand", () => ({ useBrand: () => ({ institutionName: "Example University" }) }));

// What a browser throws when a page's separately loaded file cannot be fetched: after an update,
// or when the dev server's cache of pre-bundled libraries was emptied (step 2.3).
const Missing = lazy(() =>
  Promise.reject(new TypeError("Failed to fetch dynamically imported module: /assets/Overview.js")),
);

function Broken(): never {
  throw new Error("A bug in the page");
}

function setup(start: string) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify({ status: "ok", version: "0.12.1" }))),
  );
  vi.spyOn(console, "error").mockImplementation(() => undefined);
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[start]}>
        <Routes>
          <Route element={<Layout />}>
            <Route
              path="analysis"
              element={
                <Suspense fallback={<p>Loading</p>}>
                  <Missing />
                </Suspense>
              }
            />
            <Route path="broken" element={<Broken />} />
            <Route
              path="data"
              element={
                <>
                  <h1>Data page</h1>
                  <Link to="/analysis">To Analysis</Link>
                </>
              }
            />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return userEvent.setup();
}

describe("a page that fails", () => {
  beforeEach(() => applyLanguage("en"));
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("says its file didn't load, keeps the header, and lets another page open", async () => {
    const user = setup("/data");
    await user.click(await screen.findByRole("link", { name: "To Analysis" }));
    expect(await screen.findByRole("heading", { name: "This page couldn't be shown" })).toBeInTheDocument();
    expect(screen.getByText(/Release Radar may have been updated since this tab was opened/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reload the page" })).toBeInTheDocument();
    // The app is still there: the header works, and the next page shows as usual.
    await user.click(screen.getByRole("link", { name: "Data" }));
    expect(await screen.findByRole("heading", { name: "Data page" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "This page couldn't be shown" })).not.toBeInTheDocument();
  });

  it("says something went wrong when the page itself fails", async () => {
    setup("/broken");
    expect(await screen.findByRole("heading", { name: "This page couldn't be shown" })).toBeInTheDocument();
    expect(screen.getByText(/Something went wrong while showing it/)).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
  });
});

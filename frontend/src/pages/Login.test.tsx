import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../auth";
import { applyLanguage } from "../i18n";
import Login from "./Login";

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderLogin() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter>
        <AuthProvider>
          <Login />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("sign-in page", () => {
  beforeEach(() => {
    applyLanguage("en");
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async (input) => {
        const path = String(input);
        if (path.endsWith("/auth/refresh")) return json(401, { detail: "session_expired" });
        if (path.endsWith("/auth/login")) return json(401, { detail: "invalid_credentials" });
        if (path.endsWith("/brand")) {
          return json(200, {
            theme: "Neutral",
            institution_name_en: "Example University",
            institution_name_ja: "例大学",
            logo: null,
          });
        }
        return json(404, { detail: "not_found" });
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  async function failSignIn() {
    const user = userEvent.setup();
    await user.type(await screen.findByRole("textbox"), "someone@example.org");
    await user.type(document.querySelector("#password") as HTMLElement, "wrong-password");
    await user.click(document.querySelector("button[type=submit]") as HTMLElement);
    return user;
  }

  it("explains a failed sign-in in plain language", async () => {
    renderLogin();
    await failSignIn();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "That email and password don't match. Please try again.",
    );
  });

  it("switches the whole page to Japanese with one click", async () => {
    renderLogin();
    const user = await failSignIn();
    await screen.findByRole("alert");

    await user.click(screen.getByRole("button", { name: "Switch the language to Japanese" }));

    expect(screen.getByRole("heading", { name: "サインイン" })).toBeInTheDocument();
    // A message already on screen follows the switch too.
    expect(screen.getByRole("alert")).toHaveTextContent(
      "メールアドレスとパスワードが一致しません。もう一度お試しください。",
    );
    expect(await screen.findByText("例大学")).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("ja");
    expect(screen.getByRole("button", { name: "表示言語を英語に切り替える" })).toHaveTextContent(
      "English",
    );
  });
});

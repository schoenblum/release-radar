import { expect, request as playwrightRequest, type APIRequestContext, type Locator, type Page } from "@playwright/test";

/** Synthetic people with public test passwords, made by global-setup.ts on a fresh stack. */
export const BASE_URL = process.env.BASE_URL ?? "http://localhost:8000";
export const ADMIN = { email: "admin@example.org", password: "e2e-admin-password-1" };
export const BOOTSTRAP_PASSWORD = "e2e-bootstrap-password";
export const ADA = { email: "ada@example.org", password: "e2e-ada-password-1", name: "Ada Example" };
export const BO = { email: "bo@example.org", password: "e2e-bo-password-1", name: "Bo Example" };
export const ADA_STATE = ".auth/ada.json";

export interface Release {
  id: string;
  code: string | null;
  title: string | null;
  release_type_id: string | null;
  field_versions: Record<string, number>;
  readings: { id: string; measure_key: string; value: number | null; state: string; version: number }[];
}

/** A word no other test uses, so a search shows only this test's releases. */
export function tag(): string {
  return `e2e${Date.now().toString(36)}${Math.floor(Math.random() * 1296).toString(36)}`;
}

/** A date some days ago, as the API takes it. */
export function daysAgo(days: number): string {
  const date = new Date(Date.now() - days * 86_400_000);
  return date.toISOString().slice(0, 10);
}

export class Api {
  private constructor(
    private readonly http: APIRequestContext,
    private readonly token: string,
  ) {}

  static async signIn(person: { email: string; password: string }): Promise<Api> {
    const http = await playwrightRequest.newContext({ baseURL: BASE_URL });
    const response = await http.post("/api/v1/auth/login", { data: person });
    expect(response.status(), await response.text()).toBe(200);
    const { access_token: token } = (await response.json()) as { access_token: string };
    return new Api(http, token);
  }

  private headers() {
    return { Authorization: `Bearer ${this.token}` };
  }

  async get<T>(path: string): Promise<T> {
    const response = await this.http.get(`/api/v1${path}`, { headers: this.headers() });
    expect(response.status(), await response.text()).toBe(200);
    return (await response.json()) as T;
  }

  async send<T>(method: "post" | "patch", path: string, data: unknown, status = 200): Promise<T> {
    const response = await this.http[method](`/api/v1${path}`, { headers: this.headers(), data });
    expect(response.status(), await response.text()).toBe(status);
    return (await response.json()) as T;
  }

  /** A release with these fields, saved one at a time as the grid would. */
  async release(title: string, fields: Record<string, unknown> = {}): Promise<Release> {
    let release = await this.send<Release>("post", "/releases", { title }, 201);
    for (const [field, value] of Object.entries(fields)) {
      release = await this.set(release, field, value);
    }
    return release;
  }

  async set(release: Release, field: string, value: unknown): Promise<Release> {
    const saved = await this.send<{ release: Release }>("patch", `/releases/${release.id}`, {
      field,
      value,
      version: release.field_versions[field] ?? 0,
    });
    return saved.release;
  }

  async fetch(release: Release): Promise<Release> {
    return this.get<Release>(`/releases/${release.id}`);
  }

  async dispose(): Promise<void> {
    await this.http.dispose();
  }
}

export function reading(release: Release, key: string) {
  const found = release.readings.find((item) => item.measure_key === key);
  if (!found) throw new Error(`No reading ${key}`);
  return found;
}

/** A release with a date and an EurekAlert link, so its day-28 views are due. */
export async function dueRelease(api: Api, title: string, age = 40): Promise<Release> {
  return api.release(title, {
    release_date: daysAgo(age),
    ea_url: `https://www.eurekalert.org/news-releases/${1_000_000 + Math.floor(Math.random() * 99_999)}`,
  });
}

/** The Data page narrowed to one test's releases. */
export async function openData(page: Page, word: string, view: "mine" | "all" = "all"): Promise<Locator> {
  await page.goto(`/data?view=${view}&q=${encodeURIComponent(word)}`);
  const grid = page.getByRole("grid", { name: "Releases" });
  await expect(grid).toBeVisible();
  return grid;
}

/** A cell by its row's title and its column's heading, as a person would find it. */
export async function cell(grid: Locator, title: string, heading: string | RegExp): Promise<Locator> {
  const header = grid.getByRole("columnheader", { name: heading }).first();
  const index = await header.getAttribute("aria-colindex");
  const row = grid.getByRole("row").filter({ hasText: title });
  return row.locator(`[role="gridcell"][aria-colindex="${index}"]`);
}

/** What a cell holds, without what is shown beside it (an "inferred" mark, a position chip). */
export function value(gridCell: Locator): Locator {
  return gridCell.locator(".grid-value");
}

/**
 * Put text on the clipboard the way a person does: select it somewhere and copy it. No
 * clipboard permission is involved, so this works the same in Chromium and WebKit.
 */
export async function copyText(page: Page, text: string): Promise<void> {
  await page.evaluate((value) => {
    const box = document.createElement("textarea");
    box.id = "e2e-clipboard-source";
    box.value = value;
    document.body.appendChild(box);
    box.focus();
    box.select();
  }, text);
  await page.keyboard.press("ControlOrMeta+C");
  await page.evaluate(() => document.getElementById("e2e-clipboard-source")?.remove());
}

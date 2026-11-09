import type { Language } from "../i18n";
import type {
  UserPreferences,
  Brand,
  CurrentUser,
  FieldSaved,
  ForgotPasswordResult,
  Health,
  TokenResponse,
} from "./types";

const API_PREFIX = "/api/v1";

/** A failed request. `code` is a stable identifier with a translation under `errors.`. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly body: Record<string, unknown>;

  constructor(status: number, code: string, body: Record<string, unknown> = {}) {
    super(code);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.body = body;
  }
}

// The access token lives only in memory, out of reach of anything that can read
// browser storage. The long-lived session is an httpOnly cookie (R3.3.5).
let accessToken: string | null = null;
let sessionLostListener: (() => void) | null = null;
let refreshInFlight: Promise<TokenResponse> | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function onSessionLost(listener: () => void): void {
  sessionLostListener = listener;
}

async function toApiError(response: Response): Promise<ApiError> {
  let code = "generic";
  let body: Record<string, unknown> = {};
  try {
    body = (await response.json()) as Record<string, unknown>;
    if (typeof body.detail === "string") code = body.detail;
  } catch {
    // Not JSON. The generic message applies.
  }
  return new ApiError(response.status, code, body);
}

function send(path: string, init: RequestInit): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  return fetch(`${API_PREFIX}${path}`, { ...init, headers });
}

/** Exchange the session cookie for an access token. Concurrent callers share one request. */
export function refreshSession(): Promise<TokenResponse> {
  refreshInFlight ??= (async () => {
    const response = await fetch(`${API_PREFIX}/auth/refresh`, { method: "POST" });
    if (!response.ok) throw await toApiError(response);
    const result = (await response.json()) as TokenResponse;
    accessToken = result.access_token;
    return result;
  })().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

function sessionLost(): ApiError {
  accessToken = null;
  sessionLostListener?.();
  return new ApiError(401, "session_expired");
}

async function authorized(path: string, init: RequestInit, isPublic: boolean): Promise<Response> {
  let response = await send(path, init);
  if (response.status === 401 && !isPublic) {
    try {
      await refreshSession();
    } catch (error) {
      // A network failure says nothing about the session, so that stays signed in.
      if (error instanceof ApiError && error.status === 401) throw sessionLost();
      throw error;
    }
    response = await send(path, init);
    if (response.status === 401) throw sessionLost();
  }
  if (!response.ok) throw await toApiError(response);
  return response;
}

async function request<T>(path: string, init: RequestInit = {}, isPublic = false): Promise<T> {
  const response = await authorized(path, init, isPublic);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function post(body: unknown): RequestInit {
  return { method: "POST", body: JSON.stringify(body) };
}

/** General access for the settings pages, which have many small endpoints. */
export const http = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, body === undefined ? { method: "POST" } : post(body)),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: (path: string) => request<void>(path, { method: "DELETE" }),
  /** Save one field, naming the version last seen, so a conflict can be noticed (R3.3.3). */
  patchField: (path: string, field: string, value: unknown, version: number) =>
    request<FieldSaved>(path, {
      method: "PATCH",
      body: JSON.stringify({ field, value, version }),
    }),
  /** Save what the server sends as a file. With a body, the request is a POST. */
  async download(path: string, fallbackName: string, body?: unknown): Promise<void> {
    const response = await authorized(path, body === undefined ? {} : post(body), false);
    const disposition = response.headers.get("Content-Disposition") ?? "";
    const name = /filename="([^"]+)"/.exec(disposition)?.[1] ?? fallbackName;
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
};

export const api = {
  async login(email: string, password: string): Promise<TokenResponse> {
    const result = await request<TokenResponse>("/auth/login", post({ email, password }), true);
    accessToken = result.access_token;
    return result;
  },
  async logout(): Promise<void> {
    try {
      await request<void>("/auth/logout", { method: "POST" }, true);
    } finally {
      accessToken = null;
    }
  },
  async changePassword(currentPassword: string, newPassword: string): Promise<TokenResponse> {
    const result = await request<TokenResponse>(
      "/auth/change-password",
      post({ current_password: currentPassword, new_password: newPassword }),
    );
    accessToken = result.access_token;
    return result;
  },
  forgotPassword: (email: string) =>
    request<ForgotPasswordResult>("/auth/forgot-password", post({ email }), true),
  resetPassword: (token: string, newPassword: string) =>
    request<void>("/auth/reset-password", post({ token, new_password: newPassword }), true),
  updateMe: (changes: {
    language?: Language;
    full_name?: string;
    preferences?: UserPreferences;
  }) =>
    request<CurrentUser>("/users/me", { method: "PATCH", body: JSON.stringify(changes) }),
  brand: () => request<Brand>("/brand", {}, true),
  health: () => request<Health>("/health", {}, true),
};

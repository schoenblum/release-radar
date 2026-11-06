import type { Language } from "../i18n";
import type { Brand, ForgotPasswordResult, Health, TokenResponse, User } from "./types";

const API_PREFIX = "/api/v1";

/** A failed request. `code` is a stable identifier with a translation under `errors.`. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string) {
    super(code);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
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
  try {
    const body: unknown = await response.json();
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") code = detail;
  } catch {
    // Not JSON. The generic message applies.
  }
  return new ApiError(response.status, code);
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

async function request<T>(path: string, init: RequestInit = {}, isPublic = false): Promise<T> {
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
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function post(body: unknown): RequestInit {
  return { method: "POST", body: JSON.stringify(body) };
}

export const api = {
  async login(email: string, password: string): Promise<TokenResponse> {
    const result = await request<TokenResponse>(
      "/auth/login",
      post({ email, password }),
      true,
    );
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
  updateMe: (changes: { language?: Language; full_name?: string }) =>
    request<User>("/users/me", { method: "PATCH", body: JSON.stringify(changes) }),
  brand: () => request<Brand>("/brand", {}, true),
  health: () => request<Health>("/health", {}, true),
};

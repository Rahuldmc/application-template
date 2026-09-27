/**
 * The single HTTP client. All API calls go through `api.*` so that every
 * request gets the same auth, CSRF and error handling.
 *
 * - Cookies carry the session (httpOnly; JavaScript never sees the tokens).
 * - State-changing requests send the CSRF token from the csrf_token cookie.
 * - A 401 triggers one token refresh, then the request is retried once.
 *   Refreshes are shared across concurrent requests and across browser tabs,
 *   so a rotated refresh token is never sent twice (which the backend
 *   treats as theft and ends the session).
 */
import { env } from "@/config/env";
import { readCookie } from "@/lib/cookies";

import { ApiError } from "./errors";

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
type Query = Record<string, string | number | boolean | undefined>;

interface RequestOptions {
  body?: unknown;
  query?: Query;
  signal?: AbortSignal;
}

const CSRF_COOKIE = "csrf_token";
const CSRF_HEADER = "X-CSRF-Token";
const NO_REFRESH_PATHS = ["/auth/login", "/auth/refresh", "/auth/logout"];

let onSessionExpired: () => void = () => {};

/** Called once by AuthProvider: what to do when the session can't be refreshed. */
export function setSessionExpiredHandler(handler: () => void): void {
  onSessionExpired = handler;
}

function buildUrl(path: string, query?: Query): string {
  const url = `${env.apiBaseUrl}${env.apiPrefix}${path}`;
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined) params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

async function send(method: Method, path: string, options: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") {
    const csrf = readCookie(CSRF_COOKIE);
    if (csrf) headers[CSRF_HEADER] = csrf;
  }
  return fetch(buildUrl(path, options.query), {
    method,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    credentials: "include",
    signal: options.signal,
  });
}

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const data = (await response.json()) as {
      error?: { code?: string; message?: string; details?: unknown };
    };
    if (data.error) {
      return new ApiError(
        response.status,
        data.error.code ?? "error",
        data.error.message ?? response.statusText,
        data.error.details,
      );
    }
  } catch {
    // Not JSON (e.g. a proxy error page): fall through to a generic error.
  }
  return new ApiError(response.status, "http_error", `Request failed (${response.status})`);
}

let refreshInFlight: Promise<boolean> | null = null;

async function doRefresh(): Promise<boolean> {
  const response = await send("POST", "/auth/refresh", {});
  return response.ok;
}

/** One refresh at a time per tab, and (where supported) across tabs. */
export function refreshSession(): Promise<boolean> {
  refreshInFlight ??= (async () => {
    try {
      if (typeof navigator !== "undefined" && navigator.locks) {
        return await navigator.locks.request("auth-refresh", doRefresh);
      }
      return await doRefresh();
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

async function request<T>(method: Method, path: string, options: RequestOptions = {}): Promise<T> {
  let response = await send(method, path, options);

  if (response.status === 401 && !NO_REFRESH_PATHS.includes(path)) {
    if (await refreshSession()) {
      response = await send(method, path, options);
    }
    if (response.status === 401) {
      onSessionExpired();
    }
  }

  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string, options?: Omit<RequestOptions, "body">) =>
    request<T>("GET", path, options),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>("POST", path, { ...options, body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>("PUT", path, { ...options, body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>("PATCH", path, { ...options, body }),
  delete: <T>(path: string, options?: RequestOptions) => request<T>("DELETE", path, options),
};

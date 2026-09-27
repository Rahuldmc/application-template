import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

import type { User } from "@/api/types";

export const API = "/api/v1";

export const regularUser: User = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "user@example.com",
  full_name: "Regular User",
  role: "user",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
};

export const adminUser: User = {
  ...regularUser,
  id: "22222222-2222-2222-2222-222222222222",
  email: "admin@example.com",
  full_name: "Admin User",
  role: "admin",
};

export function apiError(status: number, code: string, message: string, details?: unknown) {
  return HttpResponse.json({ error: { code, message, details } }, { status });
}

/** Default: nobody is logged in. Tests override handlers with server.use(...). */
export const server = setupServer(
  http.get(`${API}/auth/me`, () => apiError(401, "not_authenticated", "Not authenticated")),
  http.post(`${API}/auth/refresh`, () => apiError(401, "not_authenticated", "Session expired")),
  http.post(`${API}/auth/logout`, () => new HttpResponse(null, { status: 204 })),
);

export function loggedInAs(user: User) {
  server.use(http.get(`${API}/auth/me`, () => HttpResponse.json(user)));
}

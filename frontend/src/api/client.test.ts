import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { API, apiError, server } from "@/test/server";

import { api, setSessionExpiredHandler } from "./client";
import { ApiError } from "./errors";

describe("api client", () => {
  it("sends the CSRF cookie value as a header on state-changing requests", async () => {
    document.cookie = "csrf_token=abc123; path=/";
    let received: string | null = null;
    server.use(
      http.post(`${API}/things`, ({ request }) => {
        received = request.headers.get("X-CSRF-Token");
        return HttpResponse.json({ ok: true });
      }),
    );

    await api.post("/things", { a: 1 });

    expect(received).toBe("abc123");
  });

  it("does not send the CSRF header on GET", async () => {
    document.cookie = "csrf_token=abc123; path=/";
    let received: string | null = "unset";
    server.use(
      http.get(`${API}/things`, ({ request }) => {
        received = request.headers.get("X-CSRF-Token");
        return HttpResponse.json([]);
      }),
    );

    await api.get("/things");

    expect(received).toBeNull();
  });

  it("encodes query parameters and skips undefined ones", async () => {
    let url = "";
    server.use(
      http.get(`${API}/things`, ({ request }) => {
        url = request.url;
        return HttpResponse.json([]);
      }),
    );

    await api.get("/things", { query: { q: "a&b", offset: 0, skip: undefined } });

    expect(url).toContain("q=a%26b");
    expect(url).toContain("offset=0");
    expect(url).not.toContain("skip");
  });

  it("turns the backend error shape into an ApiError", async () => {
    server.use(http.get(`${API}/things`, () => apiError(409, "conflict", "Already exists")));

    const error = await api.get("/things").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 409, code: "conflict", message: "Already exists" });
  });

  it("exposes validation errors per field", async () => {
    server.use(
      http.post(`${API}/things`, () =>
        apiError(422, "validation_error", "Request validation failed", [
          { loc: ["body", "email"], msg: "Enter a valid email address", type: "value_error" },
        ]),
      ),
    );

    const error = (await api.post("/things", {}).catch((e: unknown) => e)) as ApiError;

    expect(error.fieldErrors).toEqual({ email: "Enter a valid email address" });
  });

  it("handles non-JSON error responses", async () => {
    server.use(http.get(`${API}/things`, () => new HttpResponse("Bad Gateway", { status: 502 })));

    const error = await api.get("/things").catch((e: unknown) => e);

    expect(error).toMatchObject({ status: 502, code: "http_error" });
  });

  it("refreshes once on 401 and retries the request", async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/things`, () => {
        calls += 1;
        return calls === 1
          ? apiError(401, "not_authenticated", "Not authenticated")
          : HttpResponse.json({ ok: true });
      }),
      http.post(`${API}/auth/refresh`, () => HttpResponse.json({})),
    );

    await expect(api.get("/things")).resolves.toEqual({ ok: true });
    expect(calls).toBe(2);
  });

  it("shares one refresh between concurrent 401s", async () => {
    let refreshes = 0;
    const seen = new Set<string>();
    server.use(
      http.get(`${API}/things/:id`, ({ params }) => {
        const id = String(params.id);
        if (!seen.has(id)) {
          seen.add(id);
          return apiError(401, "not_authenticated", "Not authenticated");
        }
        return HttpResponse.json({ id });
      }),
      http.post(`${API}/auth/refresh`, async () => {
        refreshes += 1;
        await new Promise((resolve) => setTimeout(resolve, 20));
        return HttpResponse.json({});
      }),
    );

    await Promise.all([api.get("/things/1"), api.get("/things/2"), api.get("/things/3")]);

    expect(refreshes).toBe(1);
  });

  it("reports an expired session when the refresh fails", async () => {
    const onExpired = vi.fn();
    setSessionExpiredHandler(onExpired);
    server.use(http.get(`${API}/things`, () => apiError(401, "not_authenticated", "Nope")));

    await expect(api.get("/things")).rejects.toMatchObject({ status: 401 });
    expect(onExpired).toHaveBeenCalledOnce();
  });

  it("never tries to refresh when login itself fails", async () => {
    const refresh = vi.fn(() => HttpResponse.json({}));
    server.use(
      http.post(`${API}/auth/login`, () =>
        apiError(401, "not_authenticated", "Invalid email or password"),
      ),
      http.post(`${API}/auth/refresh`, refresh),
    );

    await expect(api.post("/auth/login", {})).rejects.toMatchObject({ status: 401 });
    expect(refresh).not.toHaveBeenCalled();
  });
});

import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import type { UserUpdate } from "@/api/types";
import { renderApp } from "@/test/render";
import { adminUser, API, apiError, loggedInAs, regularUser, server } from "@/test/server";

const page = { items: [adminUser, regularUser], total: 2, offset: 0, limit: 20 };

describe("UsersPage", () => {
  it("is hidden from non-admins (same as the backend: looks like it doesn't exist)", async () => {
    loggedInAs(regularUser);
    renderApp("/users");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Users" })).not.toBeInTheDocument();
  });

  it("lists users for admins", async () => {
    loggedInAs(adminUser);
    server.use(http.get(`${API}/users`, () => HttpResponse.json(page)));
    renderApp("/users");

    const table = await screen.findByRole("table");
    expect(within(table).getByText("user@example.com")).toBeInTheDocument();
    expect(screen.getByText("1–2 of 2")).toBeInTheDocument();
  });

  it("disables a user and refreshes the list", async () => {
    loggedInAs(adminUser);
    let sent: UserUpdate | null = null;
    server.use(
      http.get(`${API}/users`, () => HttpResponse.json(page)),
      http.patch(`${API}/users/:id`, async ({ request }) => {
        sent = (await request.json()) as UserUpdate;
        return HttpResponse.json({ ...regularUser, is_active: false });
      }),
    );
    renderApp("/users");

    const row = (await screen.findByText("user@example.com")).closest("tr")!;
    await userEvent.click(within(row).getByRole("button", { name: "Disable" }));

    await vi.waitFor(() => expect(sent).toEqual({ is_active: false }));
  });

  it("pages through results", async () => {
    loggedInAs(adminUser);
    const offsets: string[] = [];
    server.use(
      http.get(`${API}/users`, ({ request }) => {
        const offset = new URL(request.url).searchParams.get("offset") ?? "0";
        offsets.push(offset);
        return HttpResponse.json({ ...page, total: 45, offset: Number(offset) });
      }),
    );
    renderApp("/users");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Next" }));
    expect(await screen.findByText("21–40 of 45")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Previous" }));
    expect(await screen.findByText("1–20 of 45")).toBeInTheDocument();
    expect(offsets).toContain("20");
  });

  it("shows an error when loading fails", async () => {
    loggedInAs(adminUser);
    server.use(
      http.get(`${API}/users`, () => apiError(500, "internal_error", "Something went wrong")),
    );
    renderApp("/users");
    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong");
  });
});

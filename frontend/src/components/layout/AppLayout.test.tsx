import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { renderApp } from "@/test/render";
import { adminUser, API, loggedInAs, regularUser, server } from "@/test/server";

describe("AppLayout", () => {
  it("greets a logged-in user and hides admin links from non-admins", async () => {
    loggedInAs(regularUser);
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "Welcome, Regular User" })).toBeVisible();
    expect(screen.queryByRole("link", { name: "Users" })).not.toBeInTheDocument();
  });

  it("shows admin links to admins", async () => {
    loggedInAs(adminUser);
    renderApp("/");
    expect(await screen.findByRole("link", { name: "Users" })).toBeVisible();
  });

  it("signs out on the server and returns to the login page", async () => {
    loggedInAs(regularUser);
    let loggedOut = false;
    server.use(
      http.post(`${API}/auth/logout`, () => {
        loggedOut = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { router } = renderApp("/");

    await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeVisible();
    expect(loggedOut).toBe(true);
    expect(router.state.location.pathname).toBe("/login");
  });
});

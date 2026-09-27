import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { renderApp } from "@/test/render";
import { API, apiError, regularUser, server } from "@/test/server";

async function fillAndSubmit(email: string, password: string) {
  const user = userEvent.setup();
  if (email) await user.type(await screen.findByLabelText("Email"), email);
  if (password) await user.type(screen.getByLabelText("Password"), password);
  await user.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("LoginPage", () => {
  it("redirects anonymous visitors to the login page", async () => {
    const { router } = renderApp("/");
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
  });

  it("validates input before calling the API", async () => {
    renderApp("/login");
    await fillAndSubmit("", "");
    expect(await screen.findByText("Email is required")).toBeInTheDocument();
    expect(screen.getByText("Password is required")).toBeInTheDocument();
  });

  it("shows the server's message when credentials are wrong", async () => {
    server.use(
      http.post(`${API}/auth/login`, () =>
        apiError(401, "not_authenticated", "Invalid email or password"),
      ),
    );
    renderApp("/login");

    await fillAndSubmit("user@example.com", "wrong-password");

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password");
  });

  it("logs in and returns to the page the user originally asked for", async () => {
    server.use(http.post(`${API}/auth/login`, () => HttpResponse.json(regularUser)));
    const { router } = renderApp("/some/deep/link");
    await screen.findByRole("heading", { name: "Sign in" });

    await fillAndSubmit("user@example.com", "correct-password");

    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/some/deep/link");
  });
});

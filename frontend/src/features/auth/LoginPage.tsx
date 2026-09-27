import { type FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { z } from "zod";

import { errorMessage, isApiError } from "@/api/errors";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";

import { useAuth } from "./AuthContext";

const loginSchema = z.object({
  email: z
    .string()
    .trim()
    .min(1, "Email is required")
    .includes("@", { error: "Enter a valid email" }),
  password: z.string().min(1, "Password is required"),
});

type FieldErrors = Partial<Record<"email" | "password", string>>;

/** Only allow redirects to paths inside this app (prevents open redirects). */
function safeRedirect(target: unknown): string {
  return typeof target === "string" && target.startsWith("/") && !target.startsWith("//")
    ? target
    : "/";
}

export function LoginPage() {
  const { status, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = safeRedirect((location.state as { from?: string } | null)?.from);

  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (status === "authenticated") return <Navigate to={redirectTo} replace />;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const parsed = loginSchema.safeParse({
      email: form.get("email"),
      password: form.get("password"),
    });
    if (!parsed.success) {
      const errors = z.flattenError(parsed.error).fieldErrors;
      setFieldErrors({ email: errors.email?.[0], password: errors.password?.[0] });
      return;
    }

    setFieldErrors({});
    setFormError(null);
    setSubmitting(true);
    try {
      await login(parsed.data);
      navigate(redirectTo, { replace: true });
    } catch (error) {
      setFormError(errorMessage(error));
      if (isApiError(error)) setFieldErrors(error.fieldErrors);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <form className="card" onSubmit={handleSubmit} noValidate aria-labelledby="login-title">
        <h1 id="login-title">Sign in</h1>
        {formError && <Alert>{formError}</Alert>}
        <TextField
          label="Email"
          name="email"
          type="email"
          autoComplete="username"
          error={fieldErrors.email}
        />
        <TextField
          label="Password"
          name="password"
          type="password"
          autoComplete="current-password"
          error={fieldErrors.password}
        />
        <Button type="submit" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </main>
  );
}

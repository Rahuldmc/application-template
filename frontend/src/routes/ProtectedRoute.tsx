import { Navigate, Outlet, useLocation } from "react-router";

import type { Role } from "@/api/types";
import { useAuth } from "@/features/auth/AuthContext";

import { NotFoundPage } from "./NotFoundPage";

/**
 * Gate for routes that need a logged-in user (and optionally a role).
 * This is UX only: it hides pages the user can't use. The backend is what
 * actually enforces access, on every request.
 */
export function ProtectedRoute({ roles }: { roles?: Role[] }) {
  const { status, hasRole } = useAuth();
  const location = useLocation();

  if (status === "loading") return <p aria-busy="true">Loading…</p>;
  if (status === "anonymous") {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  // Same as the backend: don't reveal that a page exists to users who can't use it.
  if (roles && !hasRole(...roles)) return <NotFoundPage />;
  return <Outlet />;
}

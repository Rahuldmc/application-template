import { useQueryClient } from "@tanstack/react-query";
import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";

import { setSessionExpiredHandler } from "@/api/client";
import type { Role, User } from "@/api/types";

import { authApi, type LoginInput } from "./api";
import { AuthContext, type AuthContextValue, type AuthStatus } from "./AuthContext";

/**
 * Holds who is logged in. The session itself lives in httpOnly cookies, so
 * on page load we simply ask the backend (`/auth/me`) who we are.
 *
 * The frontend's role checks are for UX only (hiding links and pages).
 * The backend enforces every permission.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  const clearSession = useCallback(() => {
    setUser(null);
    setStatus("anonymous");
    queryClient.clear(); // drop cached data that belonged to the old session
  }, [queryClient]);

  useEffect(() => {
    setSessionExpiredHandler(clearSession);
    let cancelled = false;
    authApi
      .me()
      .then((me) => {
        if (cancelled) return;
        setUser(me);
        setStatus("authenticated");
      })
      .catch(() => {
        if (!cancelled) setStatus("anonymous");
      });
    return () => {
      cancelled = true;
    };
  }, [clearSession]);

  const login = useCallback(async (input: LoginInput) => {
    const me = await authApi.login(input);
    setUser(me);
    setStatus("authenticated");
    return me;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      login,
      logout,
      hasRole: (...roles: Role[]) => user !== null && roles.includes(user.role),
    }),
    [status, user, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

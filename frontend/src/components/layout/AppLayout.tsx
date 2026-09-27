import { NavLink, Outlet } from "react-router";

import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";

export function AppLayout() {
  const { user, hasRole, logout } = useAuth();
  return (
    <>
      <header className="topbar">
        <nav aria-label="Main">
          <NavLink to="/" end>
            Home
          </NavLink>
          {hasRole("admin") && <NavLink to="/users">Users</NavLink>}
        </nav>
        <div className="topbar-user">
          <span>{user?.email}</span>
          <Button variant="secondary" onClick={() => void logout()}>
            Sign out
          </Button>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </>
  );
}

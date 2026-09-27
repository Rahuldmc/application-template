import { useAuth } from "@/features/auth/AuthContext";

export function HomePage() {
  const { user } = useAuth();
  return (
    <section>
      <h1>Welcome, {user?.full_name}</h1>
      <p>Start building your features in src/features/.</p>
    </section>
  );
}

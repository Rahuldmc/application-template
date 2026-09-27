// The only place import.meta.env is read. Everything here ends up in the
// public bundle, so it must never contain secrets.
export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "",
  apiPrefix: "/api/v1",
} as const;

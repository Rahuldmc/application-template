/// <reference types="vitest/config" />
import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    port: 5173,
    // The dev server forwards /api to FastAPI, so the browser sees one origin:
    // cookies just work and no CORS setup is needed. Production does the same
    // with nginx/Caddy (see deploy/).
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: false },
    },
  },
  build: {
    sourcemap: false, // don't ship readable source to clients
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/api/generated/**", "src/test/**", "src/main.tsx", "**/*.test.{ts,tsx}"],
      thresholds: { lines: 80, functions: 80, branches: 75, statements: 80 },
    },
  },
});

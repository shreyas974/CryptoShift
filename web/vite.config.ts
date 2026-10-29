/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Dev server and preview bind to 127.0.0.1 only; /api is proxied to the FastAPI backend on 127.0.0.1:8600.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8600", "/health": "http://127.0.0.1:8600", "/ready": "http://127.0.0.1:8600" },
  },
  preview: { host: "127.0.0.1", port: 4173 },
  build: { outDir: "dist", sourcemap: false, assetsInlineLimit: 0, reportCompressedSize: true },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"], // e2e/ is Playwright's
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});

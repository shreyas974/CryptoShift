import { randomBytes } from "node:crypto";
import { defineConfig } from "@playwright/test";

// A fresh random password per run for the test-only accounts of the isolated E2E backend (never stored).
process.env.E2E_PASSWORD ??= randomBytes(18).toString("base64url");

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  workers: 1,
  reporter: [["list"], ["json", { outputFile: "../scratch/derived/webapp/e2e-results.json" }]],
  use: {
    baseURL: "http://127.0.0.1:8611",
    channel: "chrome", // the Chrome already installed on this machine; no browser download
    viewport: { width: 1440, height: 900 },
    trace: "off",
  },
  webServer: {
    command: "..\\.venv\\Scripts\\python.exe e2e\\serve_e2e.py",
    url: "http://127.0.0.1:8611/health",
    reuseExistingServer: false,
    timeout: 60_000,
    env: { E2E_PASSWORD: process.env.E2E_PASSWORD },
  },
});

import { defineConfig } from "@playwright/test";
// ASTRAL_E2E_DEV=1 runs only the tagged hydration smoke against `next dev`.
const dev = process.env.ASTRAL_E2E_DEV === "1";
export default defineConfig({
  testDir: "./tests/browser",
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  ...(dev ? { grep: /@dev/ } : { grepInvert: /@dev/ }),
  use: {
    baseURL: "http://127.0.0.1:18730",
    headless: true,
    channel: "chrome",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "../.venv/bin/python tests/simulator_server.py",
      url: "http://127.0.0.1:18766/api/health",
      reuseExistingServer: false,
      gracefulShutdown: { signal: "SIGTERM", timeout: 5000 },
    },
    {
      command: dev
        ? "npx next dev --webpack --hostname 127.0.0.1 --port 18730"
        : "node .next/standalone/frontend/server.js",
      url: "http://127.0.0.1:18730",
      reuseExistingServer: false,
      timeout: dev ? 180000 : 60000,
      env: {
        HOSTNAME: "127.0.0.1",
        PORT: "18730",
        ASTRAL_API_ORIGIN: "http://127.0.0.1:18766",
        ASTRAL_HEALTH_ORIGIN: "http://127.0.0.1:18769",
        ASTRAL_INTELLIGENCE_ORIGIN: "http://127.0.0.1:18768",
        ASTRAL_UI_ORIGINS: "http://127.0.0.1:18730",
      },
      gracefulShutdown: { signal: "SIGTERM", timeout: 5000 },
    },
  ],
});

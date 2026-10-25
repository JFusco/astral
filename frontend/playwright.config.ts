import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/browser",
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
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
      command: "node .next/standalone/frontend/server.js",
      url: "http://127.0.0.1:18730",
      reuseExistingServer: false,
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

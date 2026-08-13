import { defineConfig, devices } from "@playwright/test";

// Geen `webServer`-config: frontend-bouwen regel 6b vereist dat de dev-server en de API al
// draaien vóórdat deze test start (zelfde patroon als elders in de werkwijze) — dit config
// start ze niet zelf, zowel lokaal als in CI staat dat als losse stap ervóór.
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3001",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});

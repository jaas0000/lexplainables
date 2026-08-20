import { defineConfig, devices } from "@playwright/test";

// Geen `webServer`-config: frontend-bouwen regel 6b vereist dat de dev-server en de API al
// draaien vóórdat deze test start (zelfde patroon als elders in de werkwijze) — dit config
// start ze niet zelf, zowel lokaal als in CI staat dat als losse stap ervóór.
//
// `workers: 1` in CI: veel tests loggen in als de gedeelde seed-gebruiker "beheerder"
// en muteren shared state (wachtwoord, berichten, LLM-profielen, ...). Parallel draaien
// veroorzaakt daardoor race-conditions (bv. `account.spec.ts:wachtwoord wijzigen`
// verandert het wachtwoord tijdens een andere test → login-timeout in de andere). Serieel
// draaien houdt de tests deterministisch. `fullyParallel` blijft aan zodat dev-runs snel
// zijn wanneer de tests niet elkaars state raken.
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  workers: process.env.CI ? 1 : undefined,
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

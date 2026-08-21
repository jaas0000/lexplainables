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
  // Lokale run: `list` voor korte stdout. CI: óók `html` naar `playwright-report/` zodat
  // de upload-artifact-stap een browsebare rapport-map heeft met traces + screenshots.
  reporter: process.env.CI
    ? [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]]
    : "list",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3001",
    // `retain-on-failure` (i.p.v. `on-first-retry`) bewaart de trace/screenshot/video ook
    // wanneer de test tijdens de eerste run al faalt — zonder een retry-vlag is er anders
    // geen artifact om achteraf te bekijken (fase 2b techniek-schuld: zonder deze artifacts
    // was fase 2 story 5's e2e-fout niet te debuggen).
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});

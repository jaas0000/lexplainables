# Vervolgpunten

Niet-blocking bevindingen uit code-reviews die een follow-up verdienen.

---

## Werkwijze

- **Mockup-stap in `frontend-bouwen` verbeteren**: de mockup-fase begint nu met een lege lei, terwijl het wetsanalyse-designsysteem (logobalk, navigatiebalk, kleurpalet, CSS-klassen) al vastligt. De stap zou die bestaande basis als startpunt moeten nemen zodat mockups meteen in de juiste huisstijl landen en er geen losse herstelslag nodig is.

---

## PR #5 — auth-eigen-gebruikers (story 006)

- `docs/architectuur/c4-model.md` bijwerken: L1/L2 vermelden Keycloak nog als externe service; L3 toont de oude PKCE-componenten en mist `identiteit_toegang` en de BFF-routes.
- BFF-routes controleren `session.user.rol` niet — momenteel geen `analist`-gebruikers, maar de architectuur (story 006) zegt dat de BFF de rolautorisatie draagt. Toevoegen zodra meerdere rollen in gebruik komen.

---

## PR #3 — huisstijl-frontend (story 004)

- **MEDIUM** — `.melding-fout` bypast het token-systeem: `color: rgb(213 43 30)` in
  `frontend/app/globals.css:234` is hardcoded. Fix: `color: rgb(var(--fout))`.
- **MEDIUM** — Geen `<h1>` op de pagina: de originele `<h1>Berichten beheren</h1>` is
  verwijderd; heading-hiërarchie begint nu bij `<h2>`. Accessibility-regressie voor
  screen readers. Fix: visueel verborgen `<h1>` of paginatitel boven het formulier.
- **LAAG** — `border-color` in de universele `*`-reset (`globals.css:26`) preset de
  randkleur op alle elementen; ongebruikelijk en kan onverwachte randen geven op
  elementen zonder CSS-klasse.

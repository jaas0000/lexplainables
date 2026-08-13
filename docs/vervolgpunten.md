# Vervolgpunten

Niet-blocking bevindingen uit code-reviews die een follow-up verdienen.

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

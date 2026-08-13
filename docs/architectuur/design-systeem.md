# Design-systeem — wetsanalyse

Referentiedocument voor de visuele taal van de frontend-services. Alle waarden zijn de
enige bron — pas ze hier aan, niet verspreid door de componenten. `globals.css` laadt de
CSS-variabelen; componenten refereren uitsluitend via `rgb(var(--<naam>))`.

---

## Kleurenpalet

| Token | CSS-variabele | Hex | Gebruik |
|---|---|---|---|
| paper | `--paper` | `#FFFFFF` | Pagina- en componentachtergrond |
| surface | `--surface` | `#F5F6F8` | Subtiele secties, tabelkoppen, hover |
| ink | `--ink` | `#1A1A1A` | Broodtekst |
| lint | `--lint` | `#154273` | Koppen, header, primaire merkkleur |
| muted | `--muted` | `#4A5A6E` | Secundaire tekst, subtitels |
| faint | `--faint` | `#6B7685` | Hints, placeholders, tertiaire tekst |
| line | `--line` | `#D1D6DD` | Borders, scheidingslijnen |
| accent | `--accent` | `#154273` | Primaire knoppen en interactie-elementen |
| accent-soft | `--accent-soft` | `#007BC7` | Hover-staat van primaire knoppen |
| link | `--link` | `#01689B` | Tekstlinks |

### Statusvarianten

| Token | CSS-variabele | Hex | Gebruik |
|---|---|---|---|
| succes | `--succes` | `#39870C` | Positieve status, gepubliceerd-badge |
| waarschuwing | `--waarschuwing` | `#E17000` | Waarschuwingen |
| fout | `--fout` | `#D52B1E` | Foutmeldingen, danger-knoppen |
| info | `--info` | `#007BC7` | Informatieve meldingen |

---

## Typografie

**Font:** Fira Sans (Google Fonts) — geladen via `next/font/google` in `app/layout.tsx`.

| Gewicht | Gebruik |
|---|---|
| 400 | Broodtekst |
| 500 | Labels, nav-items |
| 600 | Knoppen, tabelkoppen |
| 700 | Logo, paginatitels |

Letter-spacing voor koppen: `-0.01em`.

---

## Border-radius

| Naam | Waarde | Gebruik |
|---|---|---|
| veld | `3px` | Formuliervelden (`field-input`) |
| knop | `5px` | Knoppen (`btn`) |
| kaart | `6px` | Kaarten/secties (`card`) |
| badge | `9999px` | Status-badges (`badge`) |

---

## Knopvarianten

Gedefinieerd als CSS-klassen in `globals.css`. Basisklasse altijd `.btn`; variant ernaast.

| Klasse | Achtergrond | Tekst | Rand | Gebruik |
|---|---|---|---|---|
| `.btn-primary` | `--accent` | `--paper` | geen | Primaire actie (aanmaken, opslaan) |
| `.btn-secondary` | `--paper` | `--lint` | `--lint` | Secundaire actie (bewerken, annuleren) |
| `.btn-danger` | transparant | `--fout` | `--fout` (40%) | Destructieve actie (verwijderen) |

Minimale hoogte: `2.25rem`. Padding: `0.375rem 0.875rem`.

---

## Formuliervelden

CSS-klasse `.field-input` (input, textarea, select):

- Achtergrond: `--paper`
- Border: `1px solid rgb(var(--line))`
- Border-radius: `3px`
- Focus: `border-color: --lint` + `box-shadow: 0 0 0 3px rgb(var(--lint) / 0.15)`
- Minimale hoogte: `2.5rem`

Label boven elk veld: `.field-label` (500-gewicht, `--ink`).

---

## Navigatieheader

Achtergrond: `--lint`. Hoogte: `3.5rem`. Max-breedte inhoud: `72rem`.

Nav-items: `.nav-link` (wit, 500-gewicht). Actief item: `rgba(255 255 255 / 0.18)`.
Niet-geïmplementeerde secties: `.nav-link--placeholder` — `disabled`, `opacity: 0.45`,
`cursor: not-allowed`. Zo is direct zichtbaar wat er nog niet werkt.

---

## Bijhouden

Voeg nieuwe tokens toe als een nieuwe kleur of radius structureel nodig is — niet voor
eenmalige uitzonderingen (die horen inline). Bij een wijziging: pas eerst dit bestand aan,
dan `globals.css`, dan de componenten die de token gebruiken.

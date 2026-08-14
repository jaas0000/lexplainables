# Story 007: Admin-MCP — berichten beheren via Claude

**Prioriteit:** medium
**Story points:** 3
**Service:** `tools/wetsanalyse-admin-mcp/`

Een lichtgewicht stdio MCP-server waarmee Claude Code (of een andere MCP-client) berichten kan
aanmaken, publiceren en ophalen via de lexplainables-API, zonder daarvoor een browser te openen.

## Verhaal

Als beheerder wil ik via Claude Code een bericht kunnen aanmaken en publiceren, zodat ik snel
aankondigingen kan versturen terwijl ik toch al in de terminal werk.

## Acceptatiecriteria

- [x] `list_berichten_admin` — haalt alle berichten op (ook concepten), geeft een leesbare
      tekst terug met id, titel, type, versie, gepubliceerd-status en aanmaakdatum.
- [x] `maak_bericht(titel, inhoud, type, versie?)` — maakt een nieuw concept-bericht aan;
      `type` is één van `info | update | waarschuwing | kritiek`; `versie` is optioneel.
      Geeft het aangemaakte bericht (inclusief id) terug als tekst.
- [x] `update_bericht(id, titel, inhoud, type, versie?)` — overschrijft alle velden van een
      bestaand bericht (ook als het al gepubliceerd is). Geeft het bijgewerkte bericht terug.
- [x] `publiceer_bericht(id, gepubliceerd)` — publiceert (`gepubliceerd=true`) of
      depubliceert (`gepubliceerd=false`) een bericht op id. Geeft de bijgewerkte status terug.
- [x] Bij een API-fout (4xx/5xx) geeft de tool een leesbare foutmelding terug in de
      MCP-tekstrespons — geen ongecatchte exception.
- [x] De server start op als stdio-proces (geen HTTP-luisterpoort).
- [x] De server is registreerbaar in `.mcp.json` als:
      ```json
      {
        "wetsanalyse-admin-mcp": {
          "type": "stdio",
          "command": "node",
          "args": ["tools/wetsanalyse-admin-mcp/dist/index.js"],
          "env": {
            "LEXPLAINABLES_API_URL": "http://localhost:8000",
            "API_TOKEN": "<token>",
            "MCP_GEBRUIKERSNAAM": "beheerder"
          }
        }
      }
      ```

## Schemabeslissing

De service heeft geen eigen database. De "ene bron" zijn de Zod-inputschema's per tool in
`tools/wetsanalyse-admin-mcp/src/index.ts` — elk schema definieert tegelijk wat de MCP
ontvangt en wat er na validatie naar de API gaat. Alle drie tools zitten in één bestand
(patroon: `wetsanalyse-ai/tools/wetsanalyse-admin-mcp/src/index.ts`).

Vier tools in `TOOLS`-array:

| Tool | Input-velden | API-endpoint |
|---|---|---|
| `list_berichten_admin` | geen | `GET /v1/admin/berichten` |
| `maak_bericht` | `titel: string`, `inhoud: string`, `type: Literal[...]`, `versie?: string` | `POST /v1/admin/berichten` |
| `update_bericht` | `id: number`, `titel: string`, `inhoud: string`, `type: Literal[...]`, `versie?: string` | `PUT /v1/admin/berichten/{id}` |
| `publiceer_bericht` | `id: number`, `gepubliceerd: boolean` | `PATCH /v1/admin/berichten/{id}/publicatie` |

Teruggave van elke tool: `{ content: [{ type: "text", text: JSON.stringify(resultaat, null, 2) }] }`.

`list_berichten_admin` pakt de `items`-array uit de gepagineerde API-respons (`{ items, totaal }`)
en geeft alleen `items` terug — consistent met het referentiepatroon. `totaal` is voor deze
tool niet informatief genoeg om los te tonen.

De compileerde `dist/index.js` wordt meegecommit zodat `node dist/index.js` direct werkt.

## Auth

De server leest drie omgevingsvariabelen:

| Var | Gebruik |
|---|---|
| `LEXPLAINABLES_API_URL` | Base URL van de API (bijv. `http://localhost:8000`) |
| `API_TOKEN` | Stuurt als `Authorization: Bearer <token>` (verifieert de machine-identiteit, zie `api/app/shared/auth.py`) |
| `MCP_GEBRUIKERSNAAM` | Stuurt als `X-User-Id: <naam>` (de beheerder-gebruikersnaam in de lexplainables-database) |

De server valideert bij opstart dat alle drie ingevuld zijn; bij ontbrekende var start hij niet
en geeft een duidelijke foutmelding op stderr.

Geen roldelegatie aan de API — de API accepteert elke `X-User-Id` zolang de `API_TOKEN` klopt.
De MCP-beheerder is verantwoordelijk voor een `MCP_GEBRUIKERSNAAM` die daadwerkelijk een
beheerder is in de lexplainables-database.

## Stack

- TypeScript 7, `@modelcontextprotocol/sdk ^1.30.0` (stdio-server), `zod ^4.4.3`
- Node.js v20+, `tsc` voor de build (`dist/index.js`; gecommit)
- Geen framework, geen HTTP-server
- `package.json` + `tsconfig.json` in `tools/wetsanalyse-admin-mcp/`

## Edge cases

- `maak_bericht` met een leeg `titel` of `inhoud` → API geeft 422 terug; de tool vertaalt dat
  naar een leesbare foutmelding.
- `update_bericht` of `publiceer_bericht` met een onbekend id → API geeft 404; idem.
- `type` buiten de toegestane set → Zod-validatie weigert vóór de API-aanroep.
- Alle drie env-vars aanwezig maar API niet bereikbaar → `fetch`-fout; de tool vangt dat op en
  geeft "API niet bereikbaar" terug als tekst.

## Gedeelde logica

Geen. De vier tools delen een kleine `apiFetch`-hulpfunctie (in `src/index.ts`) die de
auth-headers toevoegt en foutresponsen normaliseert — dat is geen feature-grensoverschrijding,
het hoort bij de service-laag van deze MCP.

## Geen UI

Deze service heeft geen frontend-component. Er zijn geen gegenereerde types nodig
(`genereer-types.sh` is niet van toepassing — deze service bedient geen frontend, zie
stack-profiel §Contractgeneratie).

## Tests

Integratietests die de MCP-tools aanroepen met een lokale test-API (of een echte dev-API):
- `list_berichten_admin` → geeft een niet-lege tekst terug.
- `maak_bericht` met geldige input → API-bericht aangemaakt, id aanwezig in respons.
- `maak_bericht` met ongeldig type → Zod-validatiefout, geen API-aanroep.
- `publiceer_bericht` met onbekend id → leesbare 404-foutmelding.

**Gebouwd:** ja (gemerged)

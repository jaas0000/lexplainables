# GraphDB — de BWB-kennisgraaf

De kennisgraaf voor `tools/graph-qa` en `tools/bwb-import` (fase 4). Twee containers plus een
back-upcron; geen aparte MCP-servercontainer, want **GraphDB ≥ 11.2 heeft de MCP-server
ingebouwd** op `/mcp` (poort 7200). Het nginx'je ervoor (`mcp-auth-proxy`, poort 8004) doet de
bearer-tokencontrole voor toegang van buiten en vervangt die token door het
GraphDB-service-account — clients (bwb-import, graph-qa) kennen de echte GraphDB-credentials dus
nooit.

Referentie-architectuur: `wetsanalyse-ai/deploy/graphdb/`. Deze versie is aangepast voor lokale
ontwikkeling; zie §Productie-afwijkingen voor wat er verandert bij een echte Portainer-deploy
(ADR-0007, fase 5).

## Lokaal starten

```bash
cd deploy/graphdb
podman compose up -d      # of: docker compose up -d
```

Wacht tot de healthcheck groen is (`podman compose ps`), dan:

```bash
curl -s -u lex:lex-dev-wachtwoord http://localhost:7200/rest/repositories   # nog leeg: []
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8004/mcp          # 401 zonder token = goed
curl -s -o /dev/null -w '%{http_code}\n' -H 'Authorization: Bearer lex-dev-mcp-token' http://localhost:8004/mcp
```

**Repository `inning` moet je zelf aanmaken** (deze compose-stack doet dat niet automatisch) —
via de workbench-UI op `http://localhost:7200` (inloggen met `lex` / `lex-dev-wachtwoord`,
"Create new repository", ID `inning`) of via de REST-API. `tools/bwb-import` schrijft ernaartoe
zodra die er is.

Netwerk `graphdb_default` bestaat na het starten van deze stack; `tools/bwb-import` en
`tools/graph-qa` joinen er later als extern netwerk op en bereiken GraphDB intern op
`http://graphdb:7200`.

## Env-vars (lokale defaults, override via `.env` in deze map)

| var | lokaal default | betekenis |
|---|---|---|
| `GRAPHDB_HEAP` | `2g` | JVM-heap; bij weinig hostgeheugen lager zetten (bv. `1500m`) |
| `GRAPHDB_SVC_USER` / `GRAPHDB_SVC_PASSWORD` | `lex` / `lex-dev-wachtwoord` | GraphDB-service-account (lezen+schrijven op `inning`) |
| `MCP_BEARER_TOKEN` | `lex-dev-mcp-token` | token dat graph-qa/bwb-import moeten meesturen naar de proxy |
| `GRAPHDB_BASIC` | base64 van `lex:lex-dev-wachtwoord` | wat de proxy als Basic-auth naar GraphDB stuurt — moet horen bij `GRAPHDB_SVC_USER`/`_PASSWORD` |

## Productie-afwijkingen (fase 5, nog niet uitgevoerd)

- **Data op de docker-host, niet netwerkopslag.** GraphDB's opslaglaag gebruikt geheugen-gemapte
  bestanden en file-locking; over NFS is dat traag en kan een netwerkhapering stille
  indexcorruptie geven (Ontotext-advies). Deze lokale variant gebruikt een named volume
  (`lex-graphdb-data`) voor dev-gemak; een Portainer-deploy bindt naar een host-pad
  (`/var/lib/graphdb/home` in de referentie) of een iSCSI-LUN als het toch op de NAS moet.
- **Echte secrets, geen dev-defaults.** ADR-0006: bestandsgebaseerd (`*_FILE`-env), via
  Portainer's `secrets:`-mount. De dev-defaults hierboven (`lex-dev-wachtwoord` etc.) horen
  nergens buiten een lokale dev-machine.
- **Back-up-retentie + host-back-up-volgorde.** De RDF-dump (N-Quads, dagelijks 03:00, retentie 7)
  is applicatie-consistent; plan een host-back-up van de hele machine ná de dump zodat de verse
  dump meelift. Zie de referentie-README voor het volledige restore-recept (getest: 388.161
  triples, 7,5s herlaadtijd) en de kanttekening dat een restore de similarity-index
  (`bwb_similarity`, nodig voor `semantic_search` in graph-qa) niet meebrengt — die moet na een
  restore opnieuw gebouwd worden.

## Beveiliging

GraphDB-security staat aan: zonder credentials komt niemand bij de graaf. Twee rollen:

| account | rechten | gebruikt door |
|---|---|---|
| `admin`-achtige rol (workbench) | volledig beheer | jij, via de workbench-UI |
| service-account (`GRAPHDB_SVC_USER`) | lezen + schrijven op `inning` | de auth-proxy, de back-upcron, bwb-import |

Wie praat hoe met de graaf:
- **graph-qa / bwb-import** → `mcp-auth-proxy:8004` met hun bearer-token; de proxy controleert dat
  token en injecteert het service-account. De agent/importer kennen de GraphDB-credentials dus
  niet rechtstreeks.
- **de back-upcron** → rechtstreeks `graphdb:7200` met het service-account.
- **jij (lokaal)** → de GraphDB-workbench op `localhost:7200` met GraphDB's eigen loginscherm.

> **Security tijdelijk uitzetten** (lokaal debuggen): `curl -u lex:lex-dev-wachtwoord -X POST
> http://localhost:7200/rest/security -H 'Content-Type: application/json' -d 'false'`. Nooit in
> productie.

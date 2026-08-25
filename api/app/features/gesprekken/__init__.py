"""Gesprekken.

Wat: de persistente chatgeschiedenis van de werkplek — per gebruiker een lijst gesprekken,
elk met een geordende reeks berichten (vraag + antwoord, of een annotatieverwijzing).
Waarom: zonder dit domein leeft een gesprek alleen client-side (`conversation_id` in
React-state) — een herlaad of gesloten tabblad verliest het dan, ook als de agent zijn beurt
al had afgerond. graph-qa legt het resultaat van een beurt hier zelf vast (zie
`tools/graph-qa/agent/beurt.py`), zodat niemand aan het eind nog hoeft te kijken.
Grens: bewust los van het annotatie-domein — een bericht kan naar een annotatiedocument
verwijzen (`annotatie_slug` + het leesbare `annotatie_titel` op het moment van de beurt),
maar de review-state zelf blijft in `annotatie`. Geen rolautorisatie hier (dat draagt de
BFF); wel eigenaarschap: een gebruiker ziet en muteert alleen zijn eigen gesprekken.

Tabellen:
  - gesprekken: één rij per gesprek (id, gebruiker, titel, aangemaakt, bijgewerkt).
  - gesprek_berichten: append-only, geordend op id; de heterogene beurt-payload (tekst/denk/
    bronnen/annotatieverwijzing) staat als JSON in de kolom `inhoud`.

Beslissingen:
  - Eigenaarschap via `gebruiker` (uit `huidige_beheerder`'s `X-User-Id`), zelfde
    bearer-token+identiteit-combinatie als `chat_proxy` — sterker dan annotatie se kale
    `huidige_gebruiker`, omdat chatgeschiedenis persoonlijker is dan een agent-werkdocument.
    404 (niet 403) bij andermans gesprek — bestaan lekt niet.
  - `POST .../berichten` is idempotent op `run_id`: dezelfde agent-run mag maar één
    assistent-bericht opleveren, ook als er twee tabbladen dezelfde run volgen.

Interacties:
  - shared/auth.py: `huidige_beheerder` voor auth + eigenaarschap.
  - shared/tijd.py: `nu()` als vervangbare klok voor `aangemaakt`/`bijgewerkt`.
  - db.py: `AsyncEngine` via `get_engine()` naar de store.
  - tools/graph-qa/agent/beurt.py: enige schrijver van assistent-berichten (poort van
    wetsanalyse-ai se `agent/beurt.py::voer_beurt_uit`).
"""

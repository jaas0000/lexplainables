# Story 039: graph-qa — LLM-adapter (Anthropic via Azure AI Foundry)

**Prioriteit:** hoog
**Story points:** 3
**Service:** `tools/graph-qa/`
**Afhankelijkheid:** story 029 (poorten/config-skelet). Geen afhankelijkheid op de GraphDB-adapter
(aparte story) — de agent-loop zelf blijft buiten scope, zie hieronder.

## Verhaal

Als eerste inhoudelijke stap van `tools/graph-qa` wil ik een werkende `LLMPort`-implementatie
tegen Anthropic-modellen via Azure AI Foundry, zodat latere stories (toollaag, supervisor,
annotatieketen) tegen een échte LLM kunnen draaien in plaats van alleen tegen `FakeLLM`.

## Aanleiding

Story 029 bouwde de poorten-abstractie en markeerde de adapters zelf expliciet als buiten scope
("Letterlijk alles inhoudelijks: de LLM-/GraphDB-adapters zelf ... Zie ... voor de volledige
story-lijst (~25-35 stories geschat)"). Er is nu een geldige Azure AI Foundry-key + resource
beschikbaar (`AZURE_FOUNDRY_API_KEY_FILE`, resource `jjpl-m8ei8xzz-eastus2`), dus deze eerste
adapter kan gebouwd én tegen een levende provider geverifieerd worden.

**Correctie op story 029:** `Settings.azure_foundry_base_url` (een volledige URL, referentie-
patroon `.../anthropic`) is vervangen door `azure_foundry_resource` (de korte resource-naam,
bv. `jjpl-m8ei8xzz-eastus2`). Handmatig geverifieerd tegen de live Foundry-endpoint: de officiële
`anthropic`-Python-SDK biedt sinds kort een eigen `AnthropicFoundry`-client
(`AnthropicFoundry(api_key=..., resource=...)`) — de aanbevolen weg voor Azure AI Foundry
(dedicated provider-client, geen `Anthropic(base_url=...)`-omweg, zie de Anthropic-SDK-
documentatie). `wetsanalyse-ai`'s referentie-adapter gebruikt nog de oudere
`Anthropic(base_url=...)`-vorm (ouder dan die dedicated client); deze story wijkt daar bewust
van af — de rest van de architectuur (prompt-caching-logica, terugval-op-weigering,
stream-wrapper) volgt de referentie wél 1:1, alleen de clientconstructie verandert.

## Acceptatiecriteria

- [x] `agent/config.py`: `azure_foundry_base_url` → `azure_foundry_resource`; nieuw veld
      `prompt_caching: bool = True` (env `PROMPT_CACHING`, `"false"`/`"0"` zet 'm uit — zelfde
      patroon als andere bool-envs in het project). `require_llm()` controleert
      `azure_foundry_api_key` + `azure_foundry_resource`.
- [x] `agent/adapters/anthropic_llm.py`: `AnthropicLLM` (implementeert `LLMPort`) +
      `_AnthropicStream` (implementeert `LLMStream`), gebouwd op `AnthropicFoundry`.
- [x] Prompt-caching: het systeemblok (`Systeem = str | list[str]`) wordt bij een lijst gesplitst
      in stabiel/variabel; het cache-punt gaat op het stabiele deel, alleen als dat deel lang
      genoeg is (drempel, zelfde `_MIN_CACHE_TEKENS`-redenering als de referentie). Weigert de
      provider `cache_control` (`BadRequestError`), dan schakelt de adapter caching voor de rest
      van zijn levensduur uit en herhaalt de aanroep zonder — nooit een harde fout door caching
      alleen.
- [x] `create()` en `stream()` geven exact de vorm terug die `LLMPort`/`LLMStream` beloven
      (getest tegen de Protocols, zoals `test_ports.py` dat voor de fakes al doet).
- [x] Unit-tests (tegen een geïnjecteerde stub-client, geen netwerk): system-split-logica,
      caching-aan/uit-pad, terugval-bij-`BadRequestError` voor zowel `create()` als `stream()`.
- [x] Eén `@pytest.mark.integration`-test (standaard geskipt, zelfde conventie als
      `tools/bwb-import`): een echte `create()`-aanroep tegen de live Foundry-resource, alleen
      actief als `AZURE_FOUNDRY_API_KEY_FILE`/`AZURE_FOUNDRY_RESOURCE` in de omgeving staan.
- [x] `test_config.py` bijgewerkt voor de hernoemde/nieuwe velden.

## Buiten scope van deze story

De GraphDB-adapter (`adapters/graphdb_graph.py` + `mcp_client.py`), de toollaag, de orkestrator,
het run-model, de API-laag — zelfde lijst als story 029 §Buiten scope, op de LLM-adapter na. Ook
buiten scope: modelkeuze-tuning per rol (`LLM_MODEL_ROUTER`/`_OPHAAL`, zoals de referentie heeft)
— dat komt pas zodra er meerdere rollen zijn die een model nodig hebben.

## Ontwerp

`AnthropicLLM.__init__(self, settings: Settings, client: Any | None = None)` — `client` is
optioneel injecteerbaar (default: bouwt een echte `AnthropicFoundry` uit `settings`). Dit is de
enige afwijking van de referentie-vorm (die geen DI heeft): zonder een injectiepunt kunnen de
unit-tests de caching-/terugval-logica niet zonder netwerk toetsen, en dat is precies het gedrag
dat deze story moet bewijzen. Verder 1:1 de referentie-architectuur:

- `_system(system, *, caching=None)` — bouwt het providervriendelijke systeemblok, met het
  cache-punt op het stabiele deel (zie Acceptatiecriteria).
- `_zonder_caching(exc)` — herkent een `cache_control`-weigering, zet `self._caching = False`,
  logt één keer.
- `create()` — bij `BadRequestError` één herkansing zonder caching (via `_zonder_caching`).
- `stream()` / `_AnthropicStream` — zelfde terugvalpatroon, maar de weigering blijkt pas bij het
  openen van de stream (`__enter__`), dus de herkansing zit daar.

## Testcases

- `_system`: enkele string → ongewijzigd; lijst onder de cache-drempel → samengevoegd, geen
  cache_control; lijst boven de drempel → laatste stabiele blok krijgt `cache_control`, variabel
  deel apart; `caching=False` → nooit een cache-blok, ongeacht lengte.
- `create()`: gelukkig pad geeft de stub-response door; `BadRequestError` met `cache_control` in
  de melding → retry zonder caching, `self._caching` blijft daarna `False`; `BadRequestError`
  zonder `cache_control` in de melding → gewoon doorgooien, geen retry.
- `stream()`: gelukkig pad; `BadRequestError` bij `__enter__` → terugval zoals bij `create()`.
- `test_config.py`: `azure_foundry_resource` i.p.v. `azure_foundry_base_url` in alle bestaande
  cases; nieuwe cases voor `prompt_caching` (default aan, `PROMPT_CACHING=false` zet uit).
- Integration (geskipt tenzij env aanwezig): één echte `create()`-call, alleen assert op
  `stop_reason` + dat er tekst terugkomt — geen contentcontrole (dat hoort bij een eval, niet een
  unit-test).

## Verificatie

- `cd tools/graph-qa && uv run --extra dev pytest -q` — alle tests groen (integration geskipt
  standaard).
- `uv run --extra dev pytest -q -m integration` handmatig gedraaid met de echte Foundry-key in de
  omgeving — al bevestigd te werken vóór deze story begon (`AnthropicFoundry`-smoke-test,
  `claude-sonnet-4-6`, `stop_reason: max_tokens`, tekstblok terug).
- `uv run ruff check .` schoon.

**Gebouwd:** ja (PR volgt). `agent/config.py`: `azure_foundry_base_url` → `azure_foundry_resource`
+ nieuw `prompt_caching`-veld. Nieuw `agent/adapters/anthropic_llm.py` (`AnthropicLLM` +
`_AnthropicStream`) gebouwd op `anthropic.AnthropicFoundry`, poort van de `wetsanalyse-ai`-
referentie met de dedicated-client-afwijking uit §Ontwerp. Nieuwe `tests/test_anthropic_llm.py`
(14 tests: Protocol-conformance, `_system`-cache-logica, `create()`/`stream()` gelukkig pad +
terugval-bij-weigering, één `@pytest.mark.integration`-test). `test_config.py` bijgewerkt voor de
hernoemde/nieuwe velden. `anthropic>=1.0.0` toegevoegd aan `pyproject.toml`, `uv lock` opnieuw
gedraaid.

Geverifieerd: `uv run --extra dev pytest -q` — 35 passed, 1 skipped (integration). Handmatig met
de echte Foundry-key in de omgeving: `uv run --extra dev pytest -q -m integration` — 1 passed
(echte `create()`-call tegen `jjpl-m8ei8xzz-eastus2`, `claude-sonnet-4-6`, geldig tekstantwoord
terug). `uv run ruff check .` + `ruff format --check .` schoon.

"""LLM-profielen.

Wat: beheerders beheren benoemde LLM-configuratie-profielen (naam, provider, model, temperatuur, max_tokens) met een Fernet-versleutelde API-sleutel; profielen worden per analyse gekozen.
Waarom: eigen domein omdat een profiel meer is dan een sleutel — het combineert provider-keuze, modelparameters en credential, en meerdere profielen moeten naast elkaar bestaan (bijv. GPT-4 voor act2, Claude voor act3).
Grens: dit domein slaat profielen op en handelt sleutel-encryptie/decryptie af; de daadwerkelijke LLM-aanroep gebeurt in `engine/`, niet hier; sleutel-plaintext leeft alleen tijdens één request in-memory.

Tabellen:
  - llm_profielen: id + naam (uniek) + provider + model + temperatuur + max_tokens + api_sleutel_encrypted (Fernet) + timestamps.

Beslissingen:
  - ADR-0007 (store-abstractie): router leunt op `LlmProfielenStore` Protocol.
  - ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic + expliciete mapping.
  - Story 011 §Encryptie: Fernet-versleuteling met sleutel uit env; de sleutel-lees-fout wordt als `CryptoFout` → 500 gerapporteerd (config-fout, geen validatie).
  - Story 011 §API-response: `sleutel_ingesteld: bool` in plaats van de ciphertext of plaintext — externe caller weet dat er een sleutel is zonder hem in handen te krijgen.

Interacties:
  - shared/auth.py: `huidige_beheerder` op alle endpoints (admin-only).
  - shared/crypto.py: `versleutel_geheim` / `ontsleutel_geheim` + `CryptoFout` voor de sleutel-flow.
  - db.py: `AsyncEngine` via `get_engine()` naar de store.
"""

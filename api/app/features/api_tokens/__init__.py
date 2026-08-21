"""API-tokens.

Wat: beheerders maken en trekken API-tokens in die door externe systemen als bearer-token gebruikt worden; de plaintext-waarde is éénmalig te zien bij aanmaken, daarna alleen de prefix.
Waarom: een eigen domein omdat token-hashing, prefix-weergave en intrekken los staan van gebruikersidentiteit — een token is een aparte credential, geen kolom op de gebruiker.
Grens: dit domein zorgt alleen voor opslag/intrekking van tokens; de daadwerkelijke verificatie van een binnenkomend bearer-token gebeurt in `shared/auth.py` (`vereist_api_token`), niet hier.

Tabellen:
  - api_tokens: id + label + token_hash (SHA-256) + prefix (eerste 8 chars) + intrekker-info + timestamps.

Beslissingen:
  - ADR-0007 (store-abstractie): router leunt op `ApiTokenStore` Protocol.
  - ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic + expliciete mapping.
  - Story 018 §Geheim: plaintext-token alleen bij POST-response teruggeven; lijst-endpoint toont uitsluitend de prefix — het volledige geheim leeft nergens meer na aanmaken.

Interacties:
  - shared/auth.py: `huidige_beheerder` dependency op alle endpoints; de verificatielaag in `vereist_api_token` leest deze tabel.
  - db.py: `AsyncEngine` via `get_engine()` naar de store.
"""

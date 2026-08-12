"""Gedeelde, sterk vereenvoudigde stand-in-authenticatie (stack-profiel.md §Feature-eenheid,
`shared/`; werkwijze-feature-bouwen regel 8).

Zowel `feedback` als `berichten` hebben "wie is de ingelogde gebruiker/beheerder"-nodig. Dit
patroon heeft geen natuurlijke eigenaar-feature (het hoort niet bij Feedback of bij Bericht als
entiteit, het is puur generieke auth-simulatie) — vandaar hierheen verplaatst zodra een tweede
feature het patroon onafhankelijk nodig bleek te hebben, in plaats van het per feature te
kopiëren (feature-bouwen regel 8, "geen natuurlijke eigenaar" → `shared/<naam>.py`).

Dit is een STERK VEREENVOUDIGDE stand-in voor het echte, twee-gescheiden-schema's-auth-systeem
van deze werkwijze (werkwijze-ADR-0009: gebruikerssessies vs. service-/admin-bearer-tokens).
Deze demo simuleert beide met een simpele header, zonder sessies/JWT/bcrypt — het punt van deze
referentie-implementatie is de featurestructuur (vertical slicing, store-abstractie, migraties),
niet een volledig auth-domein namaken (dat is voorzien als latere stap, zie `BACKLOG.md`).
"""

from __future__ import annotations

from fastapi import Header


def huidige_gebruiker(x_user_id: str = Header(..., alias="X-User-Id")) -> str:
    """Vereenvoudigde stand-in voor gebruikersauthenticatie (ADR-0009): een ingelogde
    gebruiker wordt hier gesimuleerd via een header in plaats van een echte sessie."""
    return x_user_id


def huidige_beheerder(x_admin_id: str = Header(..., alias="X-Admin-Id")) -> str:
    """Vereenvoudigde stand-in voor service-/adminauthenticatie (ADR-0009): een aparte header
    in plaats van een bearer-token, om hetzelfde principe (twee gescheiden mechanismen) te
    tonen zonder een echt tokensysteem te bouwen."""
    return x_admin_id

"""Gedeeld tijdsbegrip (feature-bouwen regel 8).

`nu()` had geen natuurlijke eigenaar-feature (generiek tz-aware-now, hoort niet bij Feedback of
Bericht als entiteit) en stond identiek gekopieerd in zowel `feedback/models.py` als
`berichten/models.py` — vandaar hierheen verplaatst zodra een tweede feature het patroon
onafhankelijk nodig bleek te hebben (zelfde regel, zelfde redenering als `shared/auth.py`).
"""

from __future__ import annotations

from datetime import UTC, datetime


def nu() -> datetime:
    """Huidig moment, tz-aware (UTC). Eén plek zodat elke feature hetzelfde tijdsbegrip deelt
    in plaats van elk zijn eigen `datetime.now(UTC)`-aanroep te doen."""
    return datetime.now(UTC)

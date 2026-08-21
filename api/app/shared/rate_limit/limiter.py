"""Sliding-window teller met een harde cap op het aantal bijgehouden sleutels.

Waarom de cap: sleutels zijn vaak aanvaller-gekozen (bv. userid uit een login-poging). Zonder
cap groeit de teller-tabel onbegrensd — geheugen-DoS. Bij het bereiken van de cap veegt de
limiter eerst alle verlopen entries; blijft hij vol, dan weigeren nieuwe sleutels (fail-closed:
een aanvaller kan de limiter niet omzeilen door 'm vol te pompen — bestaande, legitieme
sleutels blijven gewoon werken).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

# Harde cap op het aantal actieve sleutels — zie module-docstring.
MAX_SLEUTELS = 10_000

_hits: dict[str, deque[float]] = defaultdict(deque)


def _veeg_verlopen(nu: float, venster_s: float) -> None:
    """Verwijder sleutels waarvan alle hits buiten het venster liggen — houdt de tabel klein."""
    verlopen_sleutels = [k for k, dq in _hits.items() if not dq or dq[0] <= nu - venster_s]
    for sleutel in verlopen_sleutels:
        dq = _hits[sleutel]
        while dq and dq[0] <= nu - venster_s:
            dq.popleft()
        if not dq:
            del _hits[sleutel]


def probeer_toestaan(sleutel: str, max_verzoeken: int, venster_s: float) -> bool:
    """Registreer een verzoek voor deze sleutel en retourneer of het binnen de limiet past.

    - `max_verzoeken <= 0` → altijd toegestaan (limiter uitgezet).
    - Retourneert `True` als het verzoek is toegestaan én de teller is opgehoogd.
    - Retourneert `False` als de limiet is bereikt of de cap-fail-closed is geraakt (in beide
      gevallen wordt de teller **niet** opgehoogd — een gaselijk toevoegen zou de aanvaller
      helpen).
    """
    if max_verzoeken <= 0:
        return True
    nu = time.monotonic()
    if sleutel not in _hits and len(_hits) >= MAX_SLEUTELS:
        _veeg_verlopen(nu, venster_s)
        if len(_hits) >= MAX_SLEUTELS:
            return False  # fail-closed: nieuwe sleutel weigert
    dq = _hits[sleutel]
    while dq and dq[0] <= nu - venster_s:
        dq.popleft()
    if len(dq) >= max_verzoeken:
        return False
    dq.append(nu)
    return True


def wis() -> None:
    """Wis alle telstaat — bedoeld voor tests. NIET gebruiken vanuit productiecode."""
    _hits.clear()

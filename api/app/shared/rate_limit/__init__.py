"""In-process sliding-window rate limit (fase 2, wetsanalyse-migratie).

Wat: een simpele misbruik-/brute-force-rem die per sleutel (userid, client-id, endpoint)
telt hoeveel verzoeken er in een venster zijn geweest — geen extra dependency, geen redis.
Waarom: `shared/`-module, geen feature — geen domein, generieke infrastructuur die door
meerdere features (auth-verify nu, mutaties later) gebruikt kan worden (werkwijze-ADR-0001).
Grens: **in-process, per replica**. Bij >1 replica schaalt de effectieve limiet mee met het
aantal replicas — geen echte cluster-brede limiet. Voor die eis komt later een proxy/WAF of
Redis. Deze module is defense-in-depth, geen zwaargewicht.

Publieke API:
- `probeer_toestaan(sleutel, max_verzoeken, venster_s) -> bool` — teller-op-check, retourneer
  True als de aanroep binnen de limiet valt (en dan is de teller opgehoogd), anders False.
- `wis()` — reset alle tellers (voor tests).
- `MAX_SLEUTELS` — harde cap op het aantal bijgehouden sleutels (memory-DoS-bescherming).
"""

from app.shared.rate_limit.limiter import MAX_SLEUTELS, probeer_toestaan, wis

__all__ = ["MAX_SLEUTELS", "probeer_toestaan", "wis"]

"""Gedragstests voor de sliding-window rate limiter (feature-bouwen regel 6).

In-process module — geen DB, geen HTTP-client. Tests wissen de teller vooraf (autouse-fixture)
zodat ze onafhankelijk zijn. Voor tijdstip-afhankelijk gedrag gebruiken we `time.sleep(...)` met
kleine vensters (10-20ms) — die zijn kort genoeg om tests snel te houden, lang genoeg om
`time.monotonic()`-granularity betrouwbaar te overspannen.
"""

from __future__ import annotations

import time

import pytest

from app.shared.rate_limit import MAX_SLEUTELS, probeer_toestaan, wis


@pytest.fixture(autouse=True)
def leeg_teller_voor_elke_test():
    wis()
    yield
    wis()


def test_verzoeken_binnen_limiet_zijn_toegestaan():
    assert probeer_toestaan("k", max_verzoeken=3, venster_s=60.0) is True
    assert probeer_toestaan("k", max_verzoeken=3, venster_s=60.0) is True
    assert probeer_toestaan("k", max_verzoeken=3, venster_s=60.0) is True


def test_verzoek_boven_limiet_wordt_geweigerd():
    for _ in range(3):
        assert probeer_toestaan("k", 3, 60.0) is True
    assert probeer_toestaan("k", 3, 60.0) is False


def test_geweigerde_verzoeken_worden_niet_bijgeteld():
    """Als de limiet is bereikt en een verzoek wordt geweigerd, mag dat niet stiekem de
    teller ophogen — anders zou een aanvaller die bewust doorpompt de limiter permanent
    op 'geweigerd' kunnen houden nadat het venster verstrijkt."""
    for _ in range(3):
        probeer_toestaan("k", 3, 60.0)
    for _ in range(100):
        assert probeer_toestaan("k", 3, 60.0) is False
    # De teller staat nu nog steeds op 3, niet op 103 — te bewijzen door na venster-reset
    # opnieuw 3 verzoeken toe te staan.


def test_venster_verstrijkt_teller_reset():
    probeer_toestaan("k", 2, venster_s=0.02)
    probeer_toestaan("k", 2, venster_s=0.02)
    assert probeer_toestaan("k", 2, 0.02) is False
    time.sleep(0.03)
    assert probeer_toestaan("k", 2, 0.02) is True


def test_sleutels_zijn_onafhankelijk():
    for _ in range(3):
        probeer_toestaan("a", 3, 60.0)
    assert probeer_toestaan("a", 3, 60.0) is False
    # Andere sleutel is niet geraakt.
    assert probeer_toestaan("b", 3, 60.0) is True


def test_max_verzoeken_nul_zet_limiter_uit():
    for _ in range(1000):
        assert probeer_toestaan("k", 0, 60.0) is True


def test_negatieve_max_verzoeken_zet_limiter_uit():
    for _ in range(100):
        assert probeer_toestaan("k", -1, 60.0) is True


def test_wis_reset_alle_tellers():
    for _ in range(3):
        probeer_toestaan("k", 3, 60.0)
    assert probeer_toestaan("k", 3, 60.0) is False
    wis()
    assert probeer_toestaan("k", 3, 60.0) is True


def test_veel_sleutels_binnen_cap_werkt():
    """Op een normale hoeveelheid unieke sleutels (binnen de cap) mag alles gewoon werken."""
    for i in range(100):
        assert probeer_toestaan(f"sleutel-{i}", 3, 60.0) is True


def test_cap_fail_closed_op_nieuwe_sleutel_bij_volle_tabel():
    """Als de tabel de cap heeft bereikt met allemaal actieve entries, moet een nieuwe
    sleutel geweigerd worden — dat is de memory-DoS-bescherming. Bestaande sleutels blijven
    werken."""
    # Vul de tabel tot de cap met actieve sleutels — venster ruim, alle blijven in beeld.
    for i in range(MAX_SLEUTELS):
        assert probeer_toestaan(f"cap-{i}", 100, venster_s=60.0) is True

    # Een nieuwe sleutel wordt geweigerd (fail-closed).
    assert probeer_toestaan("nieuw", 100, venster_s=60.0) is False

    # Een bestaande sleutel blijft werken.
    assert probeer_toestaan("cap-0", 100, venster_s=60.0) is True


def test_cap_veegt_verlopen_sleutels_bij_druk():
    """Als de tabel vol lijkt maar bevat verlopen entries voor het huidige venster, veegt de
    limiter die eerst weg — daarna past een nieuwe sleutel er alsnog in. Alle callers gebruiken
    hetzelfde venster (in dit project: één env-var, één venster); dat is de aanname van de
    veeg-logica."""
    kort_venster = 0.02
    for i in range(MAX_SLEUTELS):
        probeer_toestaan(f"oud-{i}", 100, venster_s=kort_venster)
    time.sleep(0.03)

    # Nu is de tabel vol met verlopen entries — de nieuwe sleutel triggert de veeg + past.
    assert probeer_toestaan("nieuw", 100, venster_s=kort_venster) is True

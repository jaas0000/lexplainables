from __future__ import annotations

import pytest

from app.shared.auth import GebruikerContext

TEST_BEHEERDER = GebruikerContext(gebruikersnaam="beheerder-test", rol="beheerder")


@pytest.fixture
def test_beheerder() -> GebruikerContext:
    return TEST_BEHEERDER

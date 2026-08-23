"""De IRI-ruimte van de kennisgraaf — één bron van waarheid binnen graph-qa (werkwijze-story 041).

Waarom deze module bestaat. De basis-IRI wordt door de **importer** bepaald
(`tools/bwb-import/app/rdf_vocab.py`); zonder een eigen bron zou hij hier op meerdere plekken los
overgetypt worden — als SPARQL-prefix, als filterwaarde. Kopieën van dezelfde string die niets
van elkaar weten is een kans om stil uit elkaar te lopen, en het gevolg is niet een foutmelding
maar een leeg antwoord: de `STRSTARTS`-filters matchen dan simpelweg niets.

De waarde is een eigenschap van de **data in de graaf**, niet van een sessie. Ze komt daarom uit
de omgeving (dezelfde variabelen als de importer gebruikt) en wordt bij import vastgelegd, niet
per vraag opnieuw bepaald.

`tests/test_namespace_drift.py` bewaakt dat deze defaults gelijk blijven aan
`tools/bwb-import/app/rdf_vocab.py`'s `DEFAULT_BASE_IRI`/`DEFAULT_ONTOLOGY_IRI`.

Poort van `wetsanalyse-ai/tools/graph-qa/agent/namespace.py`, 1:1.
"""

from __future__ import annotations

import os

#: Documentruimte: de IRI's van regelingen, artikelen en leden.
BASIS = os.getenv("GRAPHDB_BASE_IRI") or "urn:bwb:"

#: Vocabulaireruimte: de predicaten en klassen. Bewust géén vindplaatsen.
ONTOLOGIE = os.getenv("GRAPHDB_ONTOLOGY_IRI") or "urn:bwb-ns:"

#: Scheidingsteken tussen segmenten: ``:`` in een URN-ruimte, ``/`` in een http-IRI.
#: Spiegelt `Vocab._sep` in `tools/bwb-import/app/rdf_vocab.py`.
SEP = ":" if BASIS.startswith("urn:") else "/"

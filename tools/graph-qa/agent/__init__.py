"""graph-qa: de Juridische Assistent ("Lex").

Retrieval-augmented QA-dienst die vragen over wet- en regelgeving beantwoordt via een
GraphDB-kennisgraaf, met het antwoord uitsluitend gebaseerd op wat de graaf teruggeeft (via een
getypeerde toollaag) en achteraf gecontroleerd op brongetrouwheid.

Referentie-architectuur: wetsanalyse-ai/tools/graph-qa/ (niet 1:1 gekopieerd, zie
docs/project/stories/029-graph-qa-setup-en-poorten.md). Twee lagen: `agent/` (domein) en `api/`
(HTTP) — bewust geen `graph_qa/`-package.

Deze eerste story dekt alleen de poorten-abstractie (`ports.py`) + configuratie (`config.py`).
De agent-loop zelf (orkestrator, supervisor, toollaag, annotatieketen) volgt in latere stories.
"""

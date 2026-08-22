"""BWB-import: ETL-pipeline die het Basiswettenbestand importeert in de GraphDB-kennisgraaf.

Referentie-architectuur: wetsanalyse-ai/tools/bwb-import (niet 1:1 gekopieerd, zie
docs/project/stories/024-bwb-import-setup-en-download.md).

Pijplijn (volledig, uitgebouwd over meerdere stories):
    SRU-discovery -> toestand-XML downloaden -> XSD-validatie -> parse -> collect -> GraphDB-writer

Deze eerste story dekt alleen SRU-discovery + download + lokale cache (`app/downloader.py`).
"""

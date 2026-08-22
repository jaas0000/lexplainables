from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings
from app.downloader import BwbDownloader, DownloadError
from app.models import ToestandRef


class FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200) -> None:
        self.content = content
        self.status_code = status_code


class FakeSession:
    """Minimale requests.Session-vervanger: URL -> canned FakeResponse, geen netwerkverkeer."""

    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.headers: dict[str, str] = {}
        self._responses = responses
        self.calls: list[str] = []

    def get(self, url: str, params: dict | None = None, timeout: int | None = None) -> FakeResponse:
        self.calls.append(url)
        if url not in self._responses:
            raise AssertionError(f"Onverwachte URL aangeroepen: {url}")
        return self._responses[url]


def _sru_xml(*records: tuple[str, str, str], locatie_wti: str | None = None) -> bytes:
    """Bouw een SRU-searchRetrieveResponse met `gzd:gzd`-records.

    Elk record: (locatie_toestand, geldig_vanaf, geldig_tot). `locatie_wti` (optioneel) wordt op
    elk record meegegeven.
    """
    gzd_ns = "http://standaarden.overheid.nl/sru"
    bwb_ns = "http://standaarden.overheid.nl/bwb/terms/"
    wti_tag = f"<bwb:locatie_wti>{locatie_wti}</bwb:locatie_wti>" if locatie_wti else ""
    blocks = "".join(
        f'<gzd:gzd xmlns:gzd="{gzd_ns}" xmlns:bwb="{bwb_ns}">'
        f"<bwb:locatie_toestand>{locatie}</bwb:locatie_toestand>"
        f"<bwb:geldigheidsperiode_startdatum>{vanaf}</bwb:geldigheidsperiode_startdatum>"
        f"<bwb:geldigheidsperiode_einddatum>{tot}</bwb:geldigheidsperiode_einddatum>"
        f"{wti_tag}"
        f"</gzd:gzd>"
        for locatie, vanaf, tot in records
    )
    return f"<searchRetrieveResponse>{blocks}</searchRetrieveResponse>".encode()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        schemas_dir=tmp_path,
        sru_base_url="https://sru.test/Search",
        validate_xsd=False,
        import_wti=False,
        graphdb_url="http://graphdb:7200",
        graphdb_repository="inning",
        graphdb_user=None,
        graphdb_password=None,
        service_api_key=None,
    )


def test_discover_toestanden_sorteert_op_geldigheid(settings: Settings) -> None:
    xml = _sru_xml(
        ("https://bron.test/BWBR1/v2.xml", "2021-01-01", "2022-01-01"),
        ("https://bron.test/BWBR1/v1.xml", "2020-01-01", "2021-01-01"),
    )
    session = FakeSession({settings.sru_base_url: FakeResponse(xml)})
    downloader = BwbDownloader(settings, session=session)

    toestanden = downloader.discover_toestanden("BWBR1")

    assert [t.geldig_vanaf for t in toestanden] == ["2020-01-01", "2021-01-01"]
    assert toestanden[0].locatie_toestand == "https://bron.test/BWBR1/v1.xml"


def test_discover_toestanden_leest_locatie_wti(settings: Settings) -> None:
    xml = _sru_xml(
        ("https://bron.test/BWBR1/v1.xml", "2020-01-01", None),
        locatie_wti="https://bron.test/BWBR1/wti.xml",
    )
    session = FakeSession({settings.sru_base_url: FakeResponse(xml)})
    downloader = BwbDownloader(settings, session=session)

    toestanden = downloader.discover_toestanden("BWBR1")

    assert toestanden[0].locatie_wti == "https://bron.test/BWBR1/wti.xml"


def test_discover_toestanden_lege_respons_geeft_fout(settings: Settings) -> None:
    session = FakeSession({settings.sru_base_url: FakeResponse(b"", status_code=200)})
    downloader = BwbDownloader(settings, session=session)

    with pytest.raises(DownloadError, match="Lege SRU-respons"):
        downloader.discover_toestanden("BWBR1")


def test_discover_toestanden_geen_records_geeft_fout(settings: Settings) -> None:
    xml = b"<searchRetrieveResponse></searchRetrieveResponse>"
    session = FakeSession({settings.sru_base_url: FakeResponse(xml)})
    downloader = BwbDownloader(settings, session=session)

    with pytest.raises(DownloadError, match="Geen toestanden gevonden"):
        downloader.discover_toestanden("BWBR1")


def test_latest_toestand_geeft_meest_recente(settings: Settings) -> None:
    xml = _sru_xml(
        ("https://bron.test/BWBR1/v1.xml", "2020-01-01", "2021-01-01"),
        ("https://bron.test/BWBR1/v2.xml", "2021-01-01", None),
    )
    session = FakeSession({settings.sru_base_url: FakeResponse(xml)})
    downloader = BwbDownloader(settings, session=session)

    latest = downloader.latest_toestand("BWBR1")

    assert latest.locatie_toestand == "https://bron.test/BWBR1/v2.xml"


def test_download_toestand_schrijft_en_cachet(settings: Settings) -> None:
    xml = _sru_xml(("https://bron.test/BWBR1/v1.xml", "2020-01-01", None))
    session = FakeSession(
        {
            settings.sru_base_url: FakeResponse(xml),
            "https://bron.test/BWBR1/v1.xml": FakeResponse(b"<toestand/>"),
        }
    )
    downloader = BwbDownloader(settings, session=session)

    pad = downloader.download_toestand("BWBR1")
    assert pad.read_bytes() == b"<toestand/>"
    assert session.calls.count("https://bron.test/BWBR1/v1.xml") == 1

    # Tweede aanroep: cache-hit, geen nieuwe download.
    pad_opnieuw = downloader.download_toestand("BWBR1")
    assert pad_opnieuw == pad
    assert session.calls.count("https://bron.test/BWBR1/v1.xml") == 1


def test_download_http_fout_geeft_download_error(settings: Settings) -> None:
    xml = _sru_xml(("https://bron.test/BWBR1/v1.xml", "2020-01-01", None))
    session = FakeSession(
        {
            settings.sru_base_url: FakeResponse(xml),
            "https://bron.test/BWBR1/v1.xml": FakeResponse(b"", status_code=404),
        }
    )
    downloader = BwbDownloader(settings, session=session)

    with pytest.raises(DownloadError, match="Download mislukt"):
        downloader.download_toestand("BWBR1")


def test_download_wti_zonder_locatie_geen_netwerkcall(settings: Settings) -> None:
    session = FakeSession({})
    downloader = BwbDownloader(settings, session=session)
    ref = ToestandRef(bwb_id="BWBR1", locatie_toestand="https://bron.test/BWBR1/v1.xml")

    pad = downloader.download_wti(ref)

    assert pad is None
    assert session.calls == []


def test_download_wti_schrijft_en_cachet(settings: Settings) -> None:
    session = FakeSession({"https://bron.test/BWBR1/wti.xml": FakeResponse(b"<wti/>")})
    downloader = BwbDownloader(settings, session=session)
    ref = ToestandRef(
        bwb_id="BWBR1",
        locatie_toestand="https://bron.test/BWBR1/v1.xml",
        locatie_wti="https://bron.test/BWBR1/wti.xml",
    )

    pad = downloader.download_wti(ref)
    assert pad is not None
    assert pad.read_bytes() == b"<wti/>"
    assert session.calls.count("https://bron.test/BWBR1/wti.xml") == 1

    # Tweede aanroep: cache-hit, geen nieuwe download.
    pad_opnieuw = downloader.download_wti(ref)
    assert pad_opnieuw == pad
    assert session.calls.count("https://bron.test/BWBR1/wti.xml") == 1

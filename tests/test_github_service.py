# Tests fuer den GitHub-Dienst (mit gemocktem PyGithub)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json, base64
from unittest.mock import MagicMock, patch
from datetime import date

import github_service


def _mock_repo(counter_inhalt: dict, kunden_dateien: list[dict]) -> MagicMock:
    """Hilfsfunktion: erstellt einen gefälschten GitHub-Repo-Mock"""
    repo = MagicMock()

    counter_datei = MagicMock()
    counter_datei.decoded_content = json.dumps(counter_inhalt).encode()
    counter_datei.sha = "abc123"

    kunden_mocks = []
    for k in kunden_dateien:
        f = MagicMock()
        f.name = k["dateiname"]
        f.decoded_content = json.dumps(k["inhalt"]).encode()
        kunden_mocks.append(f)

    def get_contents(pfad):
        if pfad == "counter.json":
            return counter_datei
        if pfad == "Kunden":
            return kunden_mocks
        for k in kunden_mocks:
            if pfad == f"Kunden/{k.name}":
                return k
        raise Exception(f"Nicht gefunden: {pfad}")

    repo.get_contents.side_effect = get_contents
    return repo


def test_lese_counter_aktuelles_jahr():
    """Zähler des aktuellen Jahres wird korrekt gelesen"""
    aktuelles_jahr = date.today().year
    repo = _mock_repo({"letzteNummer": 5, "jahr": aktuelles_jahr}, [])
    nummer = github_service.lese_naechste_nummer(repo)
    assert nummer == f"RE-{aktuelles_jahr}-006"


def test_lese_counter_jahreswechsel():
    """Bei Jahreswechsel startet Zähler bei 001"""
    repo = _mock_repo({"letzteNummer": 99, "jahr": 2025}, [])
    aktuelles_jahr = date.today().year
    nummer = github_service.lese_naechste_nummer(repo)
    assert nummer == f"RE-{aktuelles_jahr}-001"


def test_lese_kunden_gibt_liste_zurueck():
    """Alle Kunden-JSONs werden als Liste zurückgegeben"""
    repo = _mock_repo(
        {"letzteNummer": 1, "jahr": 2026},
        [
            {"dateiname": "Firma_A.json", "inhalt": {"name": "Firma A", "adresse": ["Str. 1", "10000 Berlin"], "letzte_leistung": "Leistung X"}},
            {"dateiname": "Firma_B.json", "inhalt": {"name": "Firma B", "adresse": ["Str. 2", "20000 Hamburg"], "letzte_leistung": "Leistung Y"}},
        ]
    )
    kunden = github_service.lese_kunden(repo)
    assert len(kunden) == 2
    assert kunden[0]["name"] == "Firma A"
    assert kunden[1]["name"] == "Firma B"


def test_schreibe_counter_ruft_update_file_auf():
    """schreibe_counter muss update_file mit korrekter Nummer aufrufen"""
    aktuelles_jahr = date.today().year
    repo = _mock_repo({"letzteNummer": 8, "jahr": aktuelles_jahr}, [])
    github_service.schreibe_counter(repo, f"RE-{aktuelles_jahr}-009")
    assert repo.update_file.called
    call_kwargs = repo.update_file.call_args[1]
    assert call_kwargs["path"] == "counter.json"
    inhalt = json.loads(call_kwargs["content"])
    assert inhalt["letzteNummer"] == 9
    assert inhalt["jahr"] == aktuelles_jahr


def test_speichere_kunde_neu_ruft_create_file_auf():
    """Neuer Kunde → create_file muss aufgerufen werden"""
    from unittest.mock import MagicMock
    from github import GithubException
    repo = MagicMock()
    fehler = GithubException(404, {"message": "Not Found"}, None)
    repo.get_contents.side_effect = fehler
    github_service.speichere_kunde(repo, "Neue Firma", ["Str. 1", "10000 Stadt"], "Leistung")
    assert repo.create_file.called


def test_speichere_kunde_bestehend_ruft_update_file_auf():
    """Bestehender Kunde → update_file muss aufgerufen werden"""
    aktuelles_jahr = date.today().year
    repo = _mock_repo(
        {"letzteNummer": 1, "jahr": aktuelles_jahr},
        [{"dateiname": "Bestehende_Firma.json", "inhalt": {"name": "Bestehende Firma", "adresse": ["Str. 1", "10000 Stadt"], "letzte_leistung": "Alt"}}]
    )
    github_service.speichere_kunde(repo, "Bestehende Firma", ["Str. 1", "10000 Stadt"], "Neu")
    assert repo.update_file.called

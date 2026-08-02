# Tests für die seiteneffektfreie PDF-Erstellungsfunktion
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from rechnung_erstellen import erstelle_pdf_bytes

def test_erstelle_pdf_bytes_gibt_bytes_zurueck():
    """Funktion muss bytes-Objekt zurückgeben"""
    result = erstelle_pdf_bytes(
        empfaenger_name="Test GmbH",
        empfaenger_adresse=["Musterstr. 1", "12345 Berlin"],
        leistung="Testleistung",
        netto=100.0,
        mwst_betrag=19.0,
        brutto=119.0,
        rechnungsnummer="RE-2026-999",
        rechnungsdatum=date(2026, 4, 7),
    )
    assert isinstance(result, bytes)
    assert len(result) > 1000

def test_erstelle_pdf_bytes_enthaelt_pdf_header():
    """Ergebnis muss eine gueltige PDF sein"""
    result = erstelle_pdf_bytes(
        empfaenger_name="Test GmbH",
        empfaenger_adresse=["Musterstr. 1", "12345 Berlin"],
        leistung="Testleistung",
        netto=100.0,
        mwst_betrag=19.0,
        brutto=119.0,
        rechnungsnummer="RE-2026-999",
        rechnungsdatum=date(2026, 4, 7),
    )
    assert result[:4] == b"%PDF"

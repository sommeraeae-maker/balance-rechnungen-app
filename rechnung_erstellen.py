#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rechnungserstellung für BALANCE Vital-Lounge
# Legt Rechnungstext auf den bestehenden Briefbogen und speichert die fertige PDF.

import json
import os
import sys
from datetime import date
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter

# Pfade
BASIS_DIR      = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PDF   = os.path.join(BASIS_DIR, "Rechnungstemplate", "Balance_HG_Briefpapier_A4_03'21_a.pdf")
OUTPUT_DIR     = os.path.join(BASIS_DIR, "Fertige Rechnungen")
COUNTER_FILE   = os.path.join(BASIS_DIR, "counter.json")
FIRMA_FILE     = os.path.join(BASIS_DIR, "firma.json")

# ─────────────────────────────────────────────
# FIRMENDATEN UND BRIEFBOGEN
#
# Beides steht bewusst NICHT im Programmcode, damit es nicht
# versehentlich veröffentlicht wird:
#   – Auf dem Mac liegen sie als Dateien neben diesem Skript.
#   – In der Web-App werden sie beim Start hineingereicht
#     (aus den Streamlit-Secrets bzw. aus dem privaten Daten-Repo).
# ─────────────────────────────────────────────
_firma = None          # dict mit steuernummer, iban, bic, bank
_briefbogen = None     # PDF des Briefbogens als Bytes


def setze_firmendaten(firma: dict, briefbogen: bytes = None):
    """Wird von der Web-App beim Start aufgerufen und hinterlegt
    Firmendaten und Briefbogen für alle folgenden Rechnungen."""
    global _firma, _briefbogen
    _firma = firma
    if briefbogen is not None:
        _briefbogen = briefbogen


def firmendaten() -> dict:
    """Gibt die Firmendaten zurück. Auf dem Mac aus firma.json,
    in der Web-App aus dem, was setze_firmendaten() hinterlegt hat."""
    global _firma
    if _firma is None:
        with open(FIRMA_FILE, "r", encoding="utf-8") as f:
            _firma = json.load(f)
    return _firma


def briefbogen_quelle():
    """Gibt den Briefbogen zurück – entweder als Dateipfad (Mac)
    oder als Datenstrom (Web-App). Beides versteht der PDF-Leser."""
    if _briefbogen is not None:
        return BytesIO(_briefbogen)
    return TEMPLATE_PDF

# A4-Maße in Punkten (reportlab rechnet in Punkten, 1 Punkt = 1/72 Zoll)
A4_BREITE, A4_HOEHE = A4  # 595.27 x 841.89


def lade_naechste_nummer() -> tuple[str, int]:
    """Liest counter.json, erhöht Nummer, speichert zurück. Gibt (Rechnungsnummer-String, int) zurück."""
    aktuelles_jahr = date.today().year
    with open(COUNTER_FILE, "r", encoding="utf-8") as f:
        daten = json.load(f)

    # Bei Jahreswechsel Zähler zurücksetzen
    if daten.get("jahr") != aktuelles_jahr:
        daten["letzteNummer"] = 0
        daten["jahr"] = aktuelles_jahr

    daten["letzteNummer"] += 1
    nummer_int = daten["letzteNummer"]
    nummer_str = f"RE-{aktuelles_jahr}-{nummer_int:03d}"

    with open(COUNTER_FILE, "w", encoding="utf-8") as f:
        json.dump(daten, f, indent=2, ensure_ascii=False)

    return nummer_str, nummer_int


def zeichne_mehrzeiligen_text(c, x, y, text, font, size, max_breite, zeilenabstand=13):
    """Zeichnet Text mehrzeilig innerhalb der angegebenen Breite.
    Gibt die Gesamthöhe des gezeichneten Textes zurück."""
    woerter = text.split(' ')
    zeilen = []
    aktuelle_zeile = ''

    for wort in woerter:
        test_zeile = aktuelle_zeile + (' ' if aktuelle_zeile else '') + wort
        if c.stringWidth(test_zeile, font, size) <= max_breite:
            aktuelle_zeile = test_zeile
        else:
            if aktuelle_zeile:
                zeilen.append(aktuelle_zeile)
            aktuelle_zeile = wort

    if aktuelle_zeile:
        zeilen.append(aktuelle_zeile)

    c.setFont(font, size)
    for i, zeile in enumerate(zeilen):
        c.drawString(x, y - i * zeilenabstand, zeile)

    # Gesamthöhe zurückgeben (mindestens eine Zeile)
    return max(len(zeilen), 1) * zeilenabstand


def erstelle_rechnungsebene(
    empfaenger_name: str,
    empfaenger_adresse: list[str],
    leistung: str,
    netto: float,
    mwst_betrag: float,
    brutto: float,
    rechnungsnummer: str,
    rechnungsdatum: date,
) -> bytes:
    """Erstellt eine transparente PDF-Ebene mit dem Rechnungsinhalt (als Bytes)."""
    puffer = BytesIO()
    c = canvas.Canvas(puffer, pagesize=A4)

    # ── Schriftarten ──
    schrift_normal = "Helvetica"
    schrift_fett   = "Helvetica-Bold"

    # ── Empfängeradresse (Fensterbereich DIN 5008) ──
    x_links = 70
    x_adresse = 59   # fluchtet mit Absenderzeile im Briefbogen
    y_adresse = 683  # knapp unterhalb der Absenderzeile im Template

    c.setFont(schrift_normal, 9)
    c.setFillColor(colors.black)
    c.drawString(x_adresse, y_adresse, empfaenger_name)
    for i, zeile in enumerate(empfaenger_adresse):
        c.drawString(x_adresse, y_adresse - (i + 1) * 13, zeile)

    # ── Rechnungsnummer + Datum (rechtsbündig) ──
    x_rechts = A4_BREITE - 70
    y_meta = 570

    c.setFont(schrift_normal, 9)
    c.setFillColor(colors.black)
    c.drawRightString(x_rechts, y_meta,      f"Rechnungsnummer: {rechnungsnummer}")
    c.drawRightString(x_rechts, y_meta - 14, f"Datum: {rechnungsdatum.strftime('%d.%m.%Y')}")
    c.drawRightString(x_rechts, y_meta - 28, f"Steuernummer: {firmendaten()['steuernummer']}")

    # ── Überschrift RECHNUNG ──
    y_titel = 490
    c.setFont(schrift_fett, 14)
    c.setFillColor(colors.black)
    c.drawString(x_links, y_titel, "RECHNUNG")

    # ── Tabellenkopf ──
    y_tabelle = y_titel - 30
    c.setFont(schrift_fett, 9)
    c.setFillColor(colors.HexColor("#B8860B"))  # Gold-Ton passend zum Briefbogen
    c.drawString(x_links, y_tabelle,         "Position")
    c.drawString(200,      y_tabelle,         "Beschreibung")
    c.drawRightString(x_rechts, y_tabelle,    "Betrag (€)")

    # Trennlinie
    y_linie = y_tabelle - 5
    c.setStrokeColor(colors.HexColor("#B8860B"))
    c.setLineWidth(0.5)
    c.line(x_links, y_linie, x_rechts, y_linie)

    # ── Rechnungsposition (Beschreibung mehrzeilig) ──
    y_pos = y_linie - 18
    x_beschreibung = 200
    # Verfügbare Breite für Beschreibung: von x=200 bis kurz vor dem Betrag
    max_breite_beschreibung = x_rechts - x_beschreibung - 60

    c.setFillColor(colors.black)
    c.drawString(x_links, y_pos, "1")

    # Betrag rechtsbündig auf Höhe der ersten Zeile
    def fmt(zahl: float) -> str:
        return f"{zahl:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    c.setFont(schrift_normal, 9)
    c.drawRightString(x_rechts, y_pos, fmt(netto))

    # Beschreibung mehrzeilig zeichnen, Höhe merken
    text_hoehe = zeichne_mehrzeiligen_text(
        c, x_beschreibung, y_pos, leistung,
        schrift_normal, 9, max_breite_beschreibung, zeilenabstand=13
    )

    # Trennlinie nach der Beschreibung (dynamisch nach unten verschoben)
    y_linie2 = y_pos - text_hoehe - 4
    c.setStrokeColor(colors.lightgrey)
    c.setLineWidth(0.3)
    c.line(x_links, y_linie2, x_rechts, y_linie2)

    # ── Netto / MwSt / Brutto ──
    y_summen = y_linie2 - 18
    c.setFont(schrift_normal, 9)
    c.setFillColor(colors.black)

    c.drawString(350,      y_summen,       "Nettobetrag:")
    c.drawRightString(x_rechts, y_summen,  f"{fmt(netto)} €")

    c.drawString(350,      y_summen - 15,  "zzgl. 19% MwSt:")
    c.drawRightString(x_rechts, y_summen - 15, f"{fmt(mwst_betrag)} €")

    # Trennlinie vor Brutto
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.line(350, y_summen - 22, x_rechts, y_summen - 22)

    c.setFont(schrift_fett, 10)
    c.drawString(350,      y_summen - 36,  "Gesamtbetrag (Brutto):")
    c.drawRightString(x_rechts, y_summen - 36, f"{fmt(brutto)} €")

    # ── Zahlungshinweis ──
    y_zahlung = y_summen - 75
    c.setFont(schrift_normal, 8)
    c.setFillColor(colors.HexColor("#444444"))
    c.drawString(x_links, y_zahlung,
                 f"Bitte überweisen Sie den Betrag von {fmt(brutto)} € auf folgendes Konto:")
    f = firmendaten()
    c.drawString(x_links, y_zahlung - 13,
                 f"IBAN: {f['iban']}  |  BIC: {f['bic']}  |  Bank: {f['bank']}")
    c.drawString(x_links, y_zahlung - 26, f"Verwendungszweck: {rechnungsnummer}")

    c.save()
    return puffer.getvalue()


def erstelle_pdf_bytes(
    empfaenger_name: str,
    empfaenger_adresse: list[str],
    leistung: str,
    netto: float,
    mwst_betrag: float,
    brutto: float,
    rechnungsnummer: str,
    rechnungsdatum: date,
) -> bytes:
    """Erstellt die fertige Rechnung als PDF-Bytes.
    Keine Seiteneffekte: kein Zähler, keine Datei wird geschrieben.
    Wird von der Streamlit-Web-App verwendet."""

    # Rechnungsinhalt als transparente Ebene erzeugen
    ebene_bytes = erstelle_rechnungsebene(
        empfaenger_name=empfaenger_name,
        empfaenger_adresse=empfaenger_adresse,
        leistung=leistung,
        netto=netto,
        mwst_betrag=mwst_betrag,
        brutto=brutto,
        rechnungsnummer=rechnungsnummer,
        rechnungsdatum=rechnungsdatum,
    )

    # Briefbogen laden und Seite zuerst dem Writer zuweisen
    briefbogen = PdfReader(briefbogen_quelle())
    writer = PdfWriter()
    writer.add_page(briefbogen.pages[0])
    # Ebene auf die bereits zugewiesene Seite mergen
    ebene_pdf = PdfReader(BytesIO(ebene_bytes))
    writer.pages[0].merge_page(ebene_pdf.pages[0])

    # Fertige PDF als Bytes zurückgeben (keine Datei schreiben)
    puffer = BytesIO()
    writer.write(puffer)
    return puffer.getvalue()


def erstelle_rechnung(
    empfaenger_name: str,
    empfaenger_adresse: list[str],
    leistung: str,
    betrag: float,
    ist_brutto: bool,
) -> str:
    """Hauptfunktion: erstellt die fertige Rechnung und gibt den Dateipfad zurück."""

    # MwSt berechnen
    if ist_brutto:
        brutto      = betrag
        netto       = round(brutto / 1.19, 2)
        mwst_betrag = round(brutto - netto, 2)
    else:
        netto       = betrag
        mwst_betrag = round(netto * 0.19, 2)
        brutto      = round(netto + mwst_betrag, 2)

    # Rechnungsnummer holen
    rechnungsnummer, _ = lade_naechste_nummer()

    # Datum
    heute = date.today()

    # Rechnungsebene erstellen
    ebene_bytes = erstelle_rechnungsebene(
        empfaenger_name=empfaenger_name,
        empfaenger_adresse=empfaenger_adresse,
        leistung=leistung,
        netto=netto,
        mwst_betrag=mwst_betrag,
        brutto=brutto,
        rechnungsnummer=rechnungsnummer,
        rechnungsdatum=heute,
    )

    # Briefbogen laden und zuerst dem Writer zuweisen
    briefbogen = PdfReader(briefbogen_quelle())
    writer = PdfWriter()
    writer.add_page(briefbogen.pages[0])

    # Ebene einlesen und zusammenführen
    ebene_pdf = PdfReader(BytesIO(ebene_bytes))
    writer.pages[0].merge_page(ebene_pdf.pages[0])

    # Dateiname: RE-2026-001_Kundenname.pdf
    sicherer_name = empfaenger_name.replace(" ", "_").replace("/", "-").replace("\\", "-")
    dateiname = f"{rechnungsnummer}_{sicherer_name}.pdf"
    ausgabe_pfad = os.path.join(OUTPUT_DIR, dateiname)

    with open(ausgabe_pfad, "wb") as f:
        writer.write(f)

    return ausgabe_pfad, rechnungsnummer, netto, mwst_betrag, brutto


if __name__ == "__main__":
    # Wird von Claude Code mit Argumenten aufgerufen:
    # python3 rechnung_erstellen.py "Firma GmbH" "Musterstr. 1|12345 Berlin" "Sonnenstudio Oktober" "450.00" "netto"
    if len(sys.argv) != 6:
        print("FEHLER: Falsche Anzahl Argumente")
        print("Aufruf: rechnung_erstellen.py <Name> <Adresse (|getrennt)> <Leistung> <Betrag> <netto|brutto>")
        sys.exit(1)

    name      = sys.argv[1]
    adresse   = sys.argv[2].split("|")
    leistung  = sys.argv[3]
    betrag    = float(sys.argv[4].replace(",", "."))
    modus     = sys.argv[5].lower()
    ist_brutto = modus == "brutto"

    pfad, nummer, netto, mwst, brutto = erstelle_rechnung(
        empfaenger_name=name,
        empfaenger_adresse=adresse,
        leistung=leistung,
        betrag=betrag,
        ist_brutto=ist_brutto,
    )

    print(f"ERFOLG|{nummer}|{pfad}|{netto}|{mwst}|{brutto}")

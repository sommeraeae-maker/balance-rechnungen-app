# GitHub-Dienst: Zähler, Kundendaten und Fertige Rechnungen aus dem GitHub-Repo
import base64
import json
import re
from datetime import date
from github import GithubException

# Wo der Briefbogen im privaten Daten-Repo liegt
BRIEFBOGEN_PFAD = "Rechnungstemplate/Balance_HG_Briefpapier_A4_03'21_a.pdf"


def verbinde_repo(github_token: str, repo_name: str):
    """Gibt ein verbundenes PyGithub-Repo-Objekt zurück."""
    from github import Github
    g = Github(github_token)
    return g.get_repo(repo_name)


def lese_firmendaten(repo) -> dict:
    """Holt firma.json (Steuernummer, Bankverbindung) aus dem privaten Repo."""
    inhalt = repo.get_contents("firma.json")
    return json.loads(inhalt.decoded_content.decode("utf-8"))


def lese_briefbogen(repo) -> bytes:
    """Holt den Briefbogen aus dem privaten Repo.

    Der normale Weg (get_contents) funktioniert nur bis 1 MB, der Briefbogen
    ist aber rund 3,7 MB groß. Deshalb erst den Ordner auflisten, um die
    Kennung der Datei zu bekommen, und sie dann darüber herunterladen.
    """
    ordner, dateiname = BRIEFBOGEN_PFAD.rsplit("/", 1)
    for eintrag in repo.get_contents(ordner):
        if eintrag.name == dateiname:
            blob = repo.get_git_blob(eintrag.sha)
            return base64.b64decode(blob.content)
    raise FileNotFoundError(f"Briefbogen nicht gefunden: {BRIEFBOGEN_PFAD}")


def lese_naechste_nummer(repo) -> str:
    """Liest counter.json aus GitHub und gibt die NÄCHSTE Rechnungsnummer zurück.
    Schreibt noch NICHT zurück – das passiert erst nach erfolgreicher Erstellung."""
    datei = repo.get_contents("counter.json")
    daten = json.loads(datei.decoded_content)

    aktuelles_jahr = date.today().year
    if daten.get("jahr") != aktuelles_jahr:
        daten["letzteNummer"] = 0
        daten["jahr"] = aktuelles_jahr

    naechste = daten["letzteNummer"] + 1
    return f"RE-{aktuelles_jahr}-{naechste:03d}"


def schreibe_counter(repo, rechnungsnummer: str):
    """Schreibt die verwendete Rechnungsnummer als neue letzteNummer zurück nach GitHub."""
    teile = rechnungsnummer.split("-")
    jahr = int(teile[1])
    nummer = int(teile[2])

    neue_daten = {"letzteNummer": nummer, "jahr": jahr}
    datei = repo.get_contents("counter.json")
    repo.update_file(
        path="counter.json",
        message=f"Rechnungsnummer {rechnungsnummer} vergeben",
        content=json.dumps(neue_daten, indent=2, ensure_ascii=False),
        sha=datei.sha,
    )


def lese_kunden(repo) -> list:
    """Liest alle Kunden-JSON-Dateien aus Kunden/ und gibt sie als Liste zurück."""
    try:
        dateien = repo.get_contents("Kunden")
    except GithubException as e:
        if e.status == 404:
            return []
        raise

    kunden = []
    for datei in dateien:
        if datei.name.endswith(".json"):
            inhalt = json.loads(datei.decoded_content)
            inhalt["_dateiname"] = datei.name
            kunden.append(inhalt)

    return sorted(kunden, key=lambda k: k.get("name", ""))


def speichere_kunde(repo, name: str, adresse: list, letzte_leistung: str):
    """Legt einen neuen Kunden an oder aktualisiert den bestehenden in Kunden/."""
    sicherer_name = re.sub(r'[^\w\-]', '_', name)
    pfad = f"Kunden/{sicherer_name}.json"

    inhalt = {
        "name": name,
        "adresse": adresse,
        "letzte_leistung": letzte_leistung,
    }
    inhalt_str = json.dumps(inhalt, indent=2, ensure_ascii=False)

    try:
        bestehend = repo.get_contents(pfad)
        repo.update_file(
            path=pfad,
            message=f"Kundendaten aktualisiert: {name}",
            content=inhalt_str,
            sha=bestehend.sha,
        )
    except GithubException as e:
        if e.status != 404:
            raise
        repo.create_file(
            path=pfad,
            message=f"Neuer Kunde angelegt: {name}",
            content=inhalt_str,
        )


def speichere_fertige_rechnung(
    repo, pdf_bytes: bytes, rechnungsnummer: str,
    empfaenger_name: str, adresse: list, leistung: str,
    netto: float, mwst_betrag: float, brutto: float, datum
):
    """Speichert PDF und Metadaten-JSON in Fertige_Rechnungen/ im GitHub-Repo."""
    sicherer_name = re.sub(r'[^\w\-]', '_', empfaenger_name)
    basis = f"{rechnungsnummer}_{sicherer_name}"
    pdf_pfad = f"Fertige_Rechnungen/{basis}.pdf"
    json_pfad = f"Fertige_Rechnungen/{basis}.json"

    datum_str = datum.isoformat() if hasattr(datum, 'isoformat') else str(datum)
    meta = {
        "rechnungsnummer": rechnungsnummer,
        "empfaenger_name": empfaenger_name,
        "adresse": adresse,
        "leistung": leistung,
        "netto": netto,
        "mwst_betrag": mwst_betrag,
        "brutto": brutto,
        "datum": datum_str,
        "pdf_datei": f"{basis}.pdf",
    }
    meta_str = json.dumps(meta, indent=2, ensure_ascii=False)

    # PDF und Metadaten speichern (anlegen oder überschreiben)
    for pfad, inhalt in [(pdf_pfad, pdf_bytes), (json_pfad, meta_str)]:
        try:
            bestehend = repo.get_contents(pfad)
            repo.update_file(
                path=pfad,
                message=f"Rechnung {rechnungsnummer} gespeichert",
                content=inhalt,
                sha=bestehend.sha,
            )
        except GithubException as e:
            if e.status != 404:
                raise
            repo.create_file(
                path=pfad,
                message=f"Rechnung {rechnungsnummer} gespeichert",
                content=inhalt,
            )


def lese_fertige_rechnungen(repo) -> list:
    """Liest alle Metadaten-JSONs aus Fertige_Rechnungen/ und gibt sie sortiert zurück
    (neueste zuerst)."""
    try:
        dateien = repo.get_contents("Fertige_Rechnungen")
    except GithubException as e:
        if e.status == 404:
            return []
        raise

    rechnungen = []
    for datei in dateien:
        if datei.name.endswith(".json"):
            try:
                meta = json.loads(datei.decoded_content)
                rechnungen.append(meta)
            except Exception:
                pass

    return sorted(rechnungen, key=lambda r: r.get("rechnungsnummer", ""), reverse=True)


def loesche_rechnung(repo, rechnungsnummer: str):
    """Löscht PDF und JSON einer Rechnung aus Fertige_Rechnungen/ und setzt den Counter
    auf den höchsten verbleibenden Wert zurück."""
    try:
        dateien = repo.get_contents("Fertige_Rechnungen")
    except GithubException as e:
        if e.status == 404:
            return
        raise

    # Verbleibende Nummern BEVOR wir löschen berechnen
    aktuelles_jahr = date.today().year
    verbleibende_nummern = []
    zu_loeschen = []

    for datei in dateien:
        if datei.name.startswith(rechnungsnummer + "_"):
            zu_loeschen.append(datei)
        elif datei.name.endswith(".json"):
            try:
                meta = json.loads(datei.decoded_content)
                nr = meta.get("rechnungsnummer", "")
                teile = nr.split("-")
                if len(teile) == 3 and int(teile[1]) == aktuelles_jahr:
                    verbleibende_nummern.append(int(teile[2]))
            except Exception:
                pass

    # Dateien löschen
    for datei in zu_loeschen:
        repo.delete_file(
            path=datei.path,
            message=f"Rechnung {rechnungsnummer} gelöscht",
            sha=datei.sha,
        )

    # Counter auf höchste verbleibende Nummer setzen
    hoechste = max(verbleibende_nummern) if verbleibende_nummern else 0
    neue_daten = {"letzteNummer": hoechste, "jahr": aktuelles_jahr}
    counter_datei = repo.get_contents("counter.json")
    repo.update_file(
        path="counter.json",
        message=f"Counter nach Löschung von {rechnungsnummer} auf {hoechste} gesetzt",
        content=json.dumps(neue_daten, indent=2, ensure_ascii=False),
        sha=counter_datei.sha,
    )

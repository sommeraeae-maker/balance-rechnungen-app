# Streamlit-Web-App: Rechnungserstellung für BALANCE Vital-Lounge
import streamlit as st
from datetime import date, datetime
from github_service import (
    verbinde_repo, lese_naechste_nummer, schreibe_counter,
    lese_kunden, speichere_kunde,
    speichere_fertige_rechnung, lese_fertige_rechnungen, loesche_rechnung,
    lese_firmendaten, lese_briefbogen,
)
from email_service import sende_rechnung
from rechnung_erstellen import erstelle_pdf_bytes, setze_firmendaten

# ── Seitenkonfiguration ──
st.set_page_config(
    page_title="BALANCE – Rechnung erstellen",
    page_icon="🧾",
    layout="centered",
)

# ── Session-State initialisieren ──
for schluessel, standard in {
    "eingeloggt": False,
    "empfaenger_modus": None,
    "ausgewaehlter_kunde": None,
    "leistung_bestaetigt": None,
    "letzte_rechnungsnummer": None,
    "ansicht": "neue_rechnung",
    "bearbeitungs_rechnung": None,
    "bestaetige_loeschung": None,
}.items():
    if schluessel not in st.session_state:
        st.session_state[schluessel] = standard


@st.cache_resource(show_spinner="Briefbogen wird geladen …")
def firmendaten_bereitstellen():
    """Holt Briefbogen und Firmendaten einmalig aus dem privaten Daten-Repo.

    Beides liegt bewusst nicht im Programmcode dieser App, damit der Code
    öffentlich sein kann, ohne Bankverbindung oder Briefbogen preiszugeben.
    """
    repo = verbinde_repo(st.secrets["GITHUB_TOKEN"], st.secrets["GITHUB_REPO"])
    setze_firmendaten(lese_firmendaten(repo), lese_briefbogen(repo))
    return True


def zeige_navigation():
    """Zeigt die Navigationsleiste oben (nur wenn eingeloggt)."""
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown("### BALANCE Vital-Lounge")
    with col2:
        aktiv = st.session_state.ansicht == "neue_rechnung"
        if st.button("➕ Neue Rechnung", use_container_width=True,
                     type="primary" if aktiv else "secondary"):
            st.session_state.ansicht = "neue_rechnung"
            st.session_state.empfaenger_modus = None
            st.session_state.ausgewaehlter_kunde = None
            st.session_state.letzte_rechnungsnummer = None
            st.session_state.bearbeitungs_rechnung = None
            st.session_state.bestaetige_loeschung = None
            st.rerun()
    with col3:
        aktiv = st.session_state.ansicht == "fertige_rechnungen"
        if st.button("📁 Fertige Rechnungen", use_container_width=True,
                     type="primary" if aktiv else "secondary"):
            st.session_state.ansicht = "fertige_rechnungen"
            st.session_state.bearbeitungs_rechnung = None
            st.session_state.bestaetige_loeschung = None
            st.rerun()
    st.divider()


def zeige_login():
    """Zeigt das Passwortfeld an."""
    st.title("BALANCE Vital-Lounge")
    st.subheader("Rechnung erstellen")
    st.divider()
    passwort = st.text_input("Bitte Passwort eingeben:", type="password")
    if st.button("Anmelden"):
        if passwort == st.secrets["APP_PASSWORT"]:
            st.session_state.eingeloggt = True
            st.rerun()
        else:
            st.error("Falsches Passwort.")


def zeige_empfaenger_auswahl():
    """Zeigt die zwei Schaltflächen: Neuer oder Bestehender Empfänger."""
    zeige_navigation()
    st.subheader("Für wen soll die Rechnung ausgestellt werden?")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Neuer Rechnungsempfänger", use_container_width=True):
            st.session_state.empfaenger_modus = "neu"
            st.rerun()
    with col2:
        if st.button("📋 Bestehender Rechnungsempfänger", use_container_width=True):
            st.session_state.empfaenger_modus = "bestehend"
            st.rerun()


def zeige_kunden_auswahl(repo):
    """Zeigt die Liste der bestehenden Kunden zur Auswahl."""
    zeige_navigation()
    st.subheader("Kunden auswählen")
    kunden = lese_kunden(repo)

    if not kunden:
        st.warning("Noch keine Kunden gespeichert. Bitte 'Neuer Rechnungsempfänger' wählen.")
        if st.button("← Zurück"):
            st.session_state.empfaenger_modus = None
            st.rerun()
        return

    namen = [k["name"] for k in kunden]
    auswahl = st.selectbox("Kunde:", namen)
    ausgewaehlter = next(k for k in kunden if k["name"] == auswahl)

    if st.button("Weiter →"):
        st.session_state.ausgewaehlter_kunde = ausgewaehlter
        st.session_state.leistung_bestaetigt = None
        st.rerun()


def zeige_formular(repo):
    """Zeigt das Rechnungsformular und verarbeitet die Erstellung."""
    zeige_navigation()
    st.subheader("Rechnung erstellen")

    kunde = st.session_state.ausgewaehlter_kunde

    if st.session_state.empfaenger_modus == "neu":
        vorbelegung_name = ""
        vorbelegung_adr1 = ""
        vorbelegung_adr2 = ""
        vorbelegung_leistung = ""
    else:
        if kunde:
            vorbelegung_name = kunde.get("name", "")
            adr = kunde.get("adresse", ["", ""])
            vorbelegung_adr1 = adr[0] if len(adr) > 0 else ""
            vorbelegung_adr2 = adr[1] if len(adr) > 1 else ""
            vorbelegung_leistung = ""
        else:
            vorbelegung_name = ""
            vorbelegung_adr1 = ""
            vorbelegung_adr2 = ""
            vorbelegung_leistung = ""

    # Leistungstext-Bestätigung bei bestehendem Kunden
    if st.session_state.empfaenger_modus == "bestehend" and st.session_state.leistung_bestaetigt is None:
        letzte = kunde.get("letzte_leistung", "") if kunde else ""
        if letzte:
            st.info(f"**Letzter Rechnungstext:**\n\n_{letzte}_")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Ja, gleicher Text"):
                    st.session_state.leistung_bestaetigt = True
                    st.rerun()
            with col2:
                if st.button("✏️ Nein, neu schreiben"):
                    st.session_state.leistung_bestaetigt = False
                    st.rerun()
            return
        else:
            st.session_state.leistung_bestaetigt = False

    if st.session_state.empfaenger_modus == "bestehend" and st.session_state.leistung_bestaetigt:
        vorbelegung_leistung = kunde.get("letzte_leistung", "") if kunde else ""
    else:
        vorbelegung_leistung = ""

    name = st.text_input("Empfängername *", value=vorbelegung_name)
    adr1 = st.text_input("Adresszeile 1 *", value=vorbelegung_adr1)
    adr2 = st.text_input("Adresszeile 2 *", value=vorbelegung_adr2)
    leistung = st.text_area("Leistungsbeschreibung *", value=vorbelegung_leistung, height=100)
    betrag = st.number_input("Betrag (€) *", min_value=0.01, step=0.01, format="%.2f")
    modus = st.radio("Betrag ist:", ["Netto (+ 19% MwSt)", "Brutto (inkl. MwSt)"])

    st.divider()
    col_zurueck, col_erstellen = st.columns([1, 2])
    with col_zurueck:
        if st.button("← Zurück"):
            st.session_state.empfaenger_modus = None
            st.session_state.ausgewaehlter_kunde = None
            st.session_state.leistung_bestaetigt = None
            st.rerun()

    with col_erstellen:
        if st.button("🧾 Rechnung erstellen", type="primary", use_container_width=True):
            if not all([name, adr1, adr2, leistung, betrag]):
                st.error("Bitte alle Felder ausfüllen.")
                return

            ist_brutto = "Brutto" in modus
            if ist_brutto:
                brutto = betrag
                netto = round(brutto / 1.19, 2)
                mwst_betrag = round(brutto - netto, 2)
            else:
                netto = betrag
                mwst_betrag = round(netto * 0.19, 2)
                brutto = round(netto + mwst_betrag, 2)

            with st.spinner("Rechnung wird erstellt..."):
                try:
                    rechnungsnummer = lese_naechste_nummer(repo)
                    heute = date.today()

                    pdf_bytes = erstelle_pdf_bytes(
                        empfaenger_name=name,
                        empfaenger_adresse=[adr1, adr2],
                        leistung=leistung,
                        netto=netto,
                        mwst_betrag=mwst_betrag,
                        brutto=brutto,
                        rechnungsnummer=rechnungsnummer,
                        rechnungsdatum=heute,
                    )

                    # E-Mail zuerst – Counter und Speichern nur bei Erfolg
                    sende_rechnung(
                        pdf_bytes=pdf_bytes,
                        rechnungsnummer=rechnungsnummer,
                        empfaenger_name=name,
                        gmail_absender=st.secrets["GMAIL_ABSENDER"],
                        gmail_passwort=st.secrets["GMAIL_APP_PASSWORT"],
                    )

                    schreibe_counter(repo, rechnungsnummer)
                    speichere_kunde(repo, name, [adr1, adr2], leistung)
                    speichere_fertige_rechnung(
                        repo=repo,
                        pdf_bytes=pdf_bytes,
                        rechnungsnummer=rechnungsnummer,
                        empfaenger_name=name,
                        adresse=[adr1, adr2],
                        leistung=leistung,
                        netto=netto,
                        mwst_betrag=mwst_betrag,
                        brutto=brutto,
                        datum=heute,
                    )

                    st.session_state.letzte_rechnungsnummer = rechnungsnummer
                    st.session_state.empfaenger_modus = None
                    st.session_state.ausgewaehlter_kunde = None
                    st.session_state.leistung_bestaetigt = None
                    st.rerun()

                except Exception as e:
                    st.error(f"Fehler: {e}")


def zeige_fertige_rechnungen(repo):
    """Zeigt die Liste aller fertigen Rechnungen mit Optionen zum Ändern und Löschen."""
    zeige_navigation()
    st.subheader("Fertige Rechnungen")

    # Löschbestätigung anzeigen, falls aktiv
    if st.session_state.bestaetige_loeschung:
        nr = st.session_state.bestaetige_loeschung
        st.warning(f"**Rechnung {nr} wirklich löschen?** Der Rechnungszähler wird zurückgesetzt.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Ja, löschen", type="primary"):
                with st.spinner("Wird gelöscht..."):
                    loesche_rechnung(repo, nr)
                st.session_state.bestaetige_loeschung = None
                st.rerun()
        with col2:
            if st.button("Abbrechen"):
                st.session_state.bestaetige_loeschung = None
                st.rerun()
        return

    rechnungen = lese_fertige_rechnungen(repo)

    if not rechnungen:
        st.info("Noch keine Rechnungen gespeichert.")
        return

    # Tabellenkopf
    cols = st.columns([2, 3, 2, 2, 1, 1])
    for col, titel in zip(cols, ["**Nummer**", "**Empfänger**", "**Datum**", "**Brutto**", "", ""]):
        col.markdown(titel)
    st.divider()

    for rechnung in rechnungen:
        nr = rechnung.get("rechnungsnummer", "–")
        name = rechnung.get("empfaenger_name", "–")
        datum_raw = rechnung.get("datum", "")
        try:
            datum_anzeige = datetime.fromisoformat(datum_raw).strftime("%d.%m.%Y")
        except Exception:
            datum_anzeige = datum_raw
        brutto = rechnung.get("brutto", 0)
        brutto_str = f"{brutto:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

        cols = st.columns([2, 3, 2, 2, 1, 1])
        cols[0].write(nr)
        cols[1].write(name)
        cols[2].write(datum_anzeige)
        cols[3].write(brutto_str)
        with cols[4]:
            if st.button("✏️", key=f"aendern_{nr}", help="Rechnung ändern"):
                st.session_state.bearbeitungs_rechnung = rechnung
                st.rerun()
        with cols[5]:
            if st.button("🗑️", key=f"loeschen_{nr}", help="Rechnung löschen"):
                st.session_state.bestaetige_loeschung = nr
                st.rerun()


def zeige_bearbeitungs_formular(repo):
    """Zeigt das Bearbeitungsformular für eine bestehende Rechnung."""
    zeige_navigation()
    rechnung = st.session_state.bearbeitungs_rechnung
    nr = rechnung.get("rechnungsnummer", "")

    st.subheader(f"Rechnung {nr} ändern")
    st.info(f"Die Rechnungsnummer **{nr}** bleibt unverändert. Eine neue E-Mail wird verschickt.")

    name = st.text_input("Empfängername *", value=rechnung.get("empfaenger_name", ""))
    adr = rechnung.get("adresse", ["", ""])
    adr1 = st.text_input("Adresszeile 1 *", value=adr[0] if len(adr) > 0 else "")
    adr2 = st.text_input("Adresszeile 2 *", value=adr[1] if len(adr) > 1 else "")
    leistung = st.text_area("Leistungsbeschreibung *", value=rechnung.get("leistung", ""), height=100)
    betrag = st.number_input(
        "Betrag (€) *", min_value=0.01, step=0.01, format="%.2f",
        value=float(rechnung.get("brutto", 0.01)),
    )
    modus = st.radio("Betrag ist:", ["Netto (+ 19% MwSt)", "Brutto (inkl. MwSt)"], index=1)

    st.divider()
    col_zurueck, col_speichern = st.columns([1, 2])
    with col_zurueck:
        if st.button("← Zurück"):
            st.session_state.bearbeitungs_rechnung = None
            st.rerun()

    with col_speichern:
        if st.button("💾 Änderungen speichern", type="primary", use_container_width=True):
            if not all([name, adr1, adr2, leistung, betrag]):
                st.error("Bitte alle Felder ausfüllen.")
                return

            ist_brutto = "Brutto" in modus
            if ist_brutto:
                brutto = betrag
                netto = round(brutto / 1.19, 2)
                mwst_betrag = round(brutto - netto, 2)
            else:
                netto = betrag
                mwst_betrag = round(netto * 0.19, 2)
                brutto = round(netto + mwst_betrag, 2)

            # Ursprüngliches Datum beibehalten
            try:
                rechnung_datum = datetime.fromisoformat(rechnung.get("datum", "")).date()
            except Exception:
                rechnung_datum = date.today()

            with st.spinner("Rechnung wird aktualisiert..."):
                try:
                    pdf_bytes = erstelle_pdf_bytes(
                        empfaenger_name=name,
                        empfaenger_adresse=[adr1, adr2],
                        leistung=leistung,
                        netto=netto,
                        mwst_betrag=mwst_betrag,
                        brutto=brutto,
                        rechnungsnummer=nr,
                        rechnungsdatum=rechnung_datum,
                    )

                    sende_rechnung(
                        pdf_bytes=pdf_bytes,
                        rechnungsnummer=nr,
                        empfaenger_name=name,
                        gmail_absender=st.secrets["GMAIL_ABSENDER"],
                        gmail_passwort=st.secrets["GMAIL_APP_PASSWORT"],
                    )

                    # PDF und Metadaten überschreiben (Counter bleibt unverändert)
                    speichere_fertige_rechnung(
                        repo=repo,
                        pdf_bytes=pdf_bytes,
                        rechnungsnummer=nr,
                        empfaenger_name=name,
                        adresse=[adr1, adr2],
                        leistung=leistung,
                        netto=netto,
                        mwst_betrag=mwst_betrag,
                        brutto=brutto,
                        datum=rechnung_datum,
                    )

                    st.session_state.bearbeitungs_rechnung = None
                    st.session_state.letzte_rechnungsnummer = nr
                    st.rerun()

                except Exception as e:
                    st.error(f"Fehler: {e}")


def zeige_erfolg():
    """Zeigt die Bestätigungsseite nach erfolgreicher Rechnungserstellung."""
    st.title("BALANCE Vital-Lounge")
    st.divider()
    nummer = st.session_state.letzte_rechnungsnummer
    from rechnung_erstellen import firmendaten
    st.success(
        f"✅ Rechnung **{nummer}** wurde erfolgreich an "
        f"{firmendaten()['rechnung_empfaenger']} geschickt."
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Neue Rechnung erstellen"):
            st.session_state.letzte_rechnungsnummer = None
            st.session_state.ansicht = "neue_rechnung"
            st.rerun()
    with col2:
        if st.button("📁 Fertige Rechnungen anzeigen"):
            st.session_state.letzte_rechnungsnummer = None
            st.session_state.ansicht = "fertige_rechnungen"
            st.rerun()


# ── Haupt-Routing ──
if st.session_state.eingeloggt:
    # Briefbogen und Firmendaten einmalig nachladen
    firmendaten_bereitstellen()

if not st.session_state.eingeloggt:
    zeige_login()
elif st.session_state.letzte_rechnungsnummer is not None:
    zeige_erfolg()
elif st.session_state.ansicht == "fertige_rechnungen":
    repo = verbinde_repo(st.secrets["GITHUB_TOKEN"], st.secrets["GITHUB_REPO"])
    if st.session_state.bearbeitungs_rechnung is not None:
        zeige_bearbeitungs_formular(repo)
    else:
        zeige_fertige_rechnungen(repo)
else:
    # Ansicht: neue_rechnung
    if st.session_state.empfaenger_modus is None:
        zeige_empfaenger_auswahl()
    elif st.session_state.empfaenger_modus == "bestehend" and st.session_state.ausgewaehlter_kunde is None:
        repo = verbinde_repo(st.secrets["GITHUB_TOKEN"], st.secrets["GITHUB_REPO"])
        zeige_kunden_auswahl(repo)
    else:
        repo = verbinde_repo(st.secrets["GITHUB_TOKEN"], st.secrets["GITHUB_REPO"])
        zeige_formular(repo)

# E-Mail-Dienst: fertige Rechnung als PDF per Gmail verschicken
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# Der Empfänger steht in firma.json (privates Daten-Repo), nicht im Code.
def _empfaenger() -> str:
    from rechnung_erstellen import firmendaten
    return firmendaten()["rechnung_empfaenger"]


def sende_rechnung(
    pdf_bytes: bytes,
    rechnungsnummer: str,
    empfaenger_name: str,
    gmail_absender: str,
    gmail_passwort: str,
):
    """Verschickt die Rechnung als PDF-Anhang per Gmail."""
    nachricht = MIMEMultipart()
    nachricht["From"] = gmail_absender
    empfaenger = _empfaenger()
    nachricht["To"] = empfaenger
    nachricht["Subject"] = f"Rechnung {rechnungsnummer} – BALANCE Vital-Lounge"

    text = (
        f"Hallo,\n\n"
        f"anbei die Rechnung {rechnungsnummer} für {empfaenger_name}.\n\n"
        f"Viele Grüße\nBALANCE Vital-Lounge"
    )
    nachricht.attach(MIMEText(text, "plain", "utf-8"))

    anhang = MIMEBase("application", "octet-stream")
    anhang.set_payload(pdf_bytes)
    encoders.encode_base64(anhang)
    anhang.add_header(
        "Content-Disposition",
        f"attachment; filename={rechnungsnummer}_{empfaenger_name.replace(' ', '_')}.pdf",
    )
    nachricht.attach(anhang)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_absender, gmail_passwort)
        server.sendmail(gmail_absender, empfaenger, nachricht.as_string())

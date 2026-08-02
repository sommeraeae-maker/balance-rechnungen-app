# Tests fuer den E-Mail-Dienst (smtplib wird gemockt)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
import pytest
import email_service
import rechnung_erstellen


@pytest.fixture(autouse=True)
def firmendaten_zuruecksetzen():
    """Nach dem Test die vorgegebenen Firmendaten wieder entfernen,
    damit andere Tests weiterhin die echte firma.json verwenden."""
    yield
    rechnung_erstellen._firma = None


def test_sende_rechnung_baut_korrekte_mail():
    """Prüft dass die E-Mail korrekt aufgebaut und abgeschickt wird"""
    fake_pdf = b"%PDF-1.4 fake content"

    # Firmendaten vorgeben, damit der Test nicht von firma.json abhängt
    rechnung_erstellen.setze_firmendaten({"rechnung_empfaenger": "test-empfaenger@example.de"})

    with patch("smtplib.SMTP_SSL") as mock_smtp_klasse:
        mock_smtp = MagicMock()
        mock_smtp_klasse.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_klasse.return_value.__exit__ = MagicMock(return_value=False)

        email_service.sende_rechnung(
            pdf_bytes=fake_pdf,
            rechnungsnummer="RE-2026-009",
            empfaenger_name="Test GmbH",
            gmail_absender="test@gmail.com",
            gmail_passwort="geheim",
        )

        assert mock_smtp.sendmail.called
        args = mock_smtp.sendmail.call_args
        absender = args[0][0]
        empfaenger = args[0][1]
        assert absender == "test@gmail.com"
        assert empfaenger == "test-empfaenger@example.de"

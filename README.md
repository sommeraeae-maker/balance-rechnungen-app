# BALANCE Vital-Lounge – Rechnungs-App

Web-App zur Rechnungserstellung. Enthält **nur Programmcode**.

## Wo liegt was?

| Repo | Inhalt |
|---|---|
| Dieses Repo (öffentlich) | Der Programmcode der App |
| `balance-rechnungen` (privat) | Kundendaten, fertige Rechnungen, Briefbogen, Firmendaten |

Kundendaten, Bankverbindung und Briefbogen stehen bewusst **nicht** in diesem Repo.
Die App lädt sie beim Start aus dem privaten Repo nach.

## Deployment

Läuft auf Streamlit Community Cloud. Benötigte Secrets:

```toml
APP_PASSWORT = "..."
GITHUB_TOKEN = "..."         # Zugriff auf das private Daten-Repo
GITHUB_REPO = "sommeraeae-maker/balance-rechnungen"
GMAIL_ABSENDER = "..."       # nur fuer den Mailversand
GMAIL_APP_PASSWORT = "..."   # nur fuer den Mailversand
```

## Tests

```bash
python3 -m pytest tests/ -q
```

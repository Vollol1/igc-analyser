# ADR-001: Architecture & Tech Stack

## Status

Active

## Context

igc-extractor soll Paragliding-Flugtracks (`.igc`) von dhv-xc.de herunterladen und lokal verfügbar machen. Dafür müssen wir uns für einen anwendungstechnisch schlanken Stack, ein lokales Speicherformat sowie einen robusten, wiederholbaren Ausführungsmodus entscheiden. Ein wichtiger weiterer Aspekt ist der Umgang mit Credentials, da das Tool einen Login bei dhv-xc.de benötigt.

## Decision

### Language & scraping

- **Python 3** als Implementierungssprache.
- **requests** für HTTP(S)-Aufrufe (Login, Flugliste, IGC-Download).
- **BeautifulSoup 4** mit dem **lxml**-Parser zum Parsen der HTML-Seiten von dhv-xc.de.

### Lokale Speicherung

- **SQLite** als kleine, portable Statusdatenbank für bereits verarbeitete Flüge, Fehlerzähler und Resume-Informationen.
- **JSONL** als Ausgabeformat für extrahierte Flugmetadaten (geeignet für stappende, zeilenbasierte Weiterverarbeitung).
- Heruntergeladene `.igc`-Dateien landen als Dateien im Dateisystem unter `data/igc/`.

### Ausführung

- **Idempotenz**: gleiche Eingabe führt bei wiederholtem Lauf zum gleichen Ergebnis; Dateien werden nicht doppelt heruntergeladen, Metadaten werden konsolidiert.
- **Resume**: ein abgebrochener Lauf kann fortgesetzt werden; erfolgreiche Schritte werden übersprungen.
- CLI-first: primäres Interface ist ein Python-Skript unter `scripts/igc_extractor.py`.

### Secrets & Credentials

- Credentials (dhv-xc.de Benutzername/Passwort) werden ausschließlich über Umgebungsvariablen oder eine lokale `.env`-Datei bezogen.
- `.env` wird in `.gitignore` ignoriert und niemals committet.
- Es werden keine Secrets im Quellcode, in Log-Dateien oder im State gespeichert.
- Details und Notfall-Handling bei einem versehentlichen Leak folgen dem Vorbild von [gag-atlas ADR-007: Secrets-Management](/home/florian/github.com/Vollol1/gag-atlas/docs/decisions/ADR-007-secrets-management.md).

### Optional / later

- **python-dotenv** (optional) zum bequemen Laden von `.env` in lokale Entwicklungsumgebungen.
- **tqdm** (optional) für Fortschrittsanzeigen bei langen Batch-Läufen.
- Keine externen Cloud-APIs für die Kernpipeline vorgesehen.

## Consequences

### Positive

- Sehr geringer Deployment-Aufwand: Python-venv plus Abhängigkeiten aus `requirements.txt` genügt.
- SQLite und JSONL benötigen keinen laufenden Server und sind portabel.
- Parser-basiertes HTML-Scraping ist deterministisch, reproduzierbar und offline-debuggbar.
- Idempotenz + Resume sparen Bandbreite und Zeit bei wiederholten Läufen.
- Klare Trennung von Code und Credentials minimiert das Risiko von Leaks.

### Negative

- HTML-Scraping ist von der Struktur von dhv-xc.de abhängig; Layout-Änderungen erfordern Anpassungen.
- Ohne Cloud-Fallback ist die Verarbeitung an lokale Ressourcen gebunden.
- `.env`-Handling muss bei jedem neuen Mitentwickler kommuniziert werden (siehe gag-atlas ADR-007).

## References

- [gag-atlas ADR-007: Secrets-Management](/home/florian/github.com/Vollol1/gag-atlas/docs/decisions/ADR-007-secrets-management.md)
- [Python requests](https://requests.readthedocs.io/)
- [BeautifulSoup 4](https://www.crummy.com/software/BeautifulSoup/)
- [lxml parser](https://lxml.de/)

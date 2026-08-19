# igc-extractor v1.0.0 — Public Release

Erstes öffentliches Release von **igc-extractor** — einem schlanken, lokalen Python-CLI-Tool zum Herunterladen, Archivieren und Visualisieren eigener Paragliding-/Gleitschirm-Flugtracks im IGC-Format.

## Was igc-extractor macht

- Meldet sich mit deinen persönlichen Zugangsdaten bei [dhv-xc.de](https://www.dhv-xc.de) an.
- Lädt **alle eigenen Flüge** eines Accounts (inkl. privater Flüge) als `.igc`-Dateien herunter.
- Speichert Flugmetadaten lokal als JSONL und SQLite.
- Erzeugt ein strukturiertes ZIP-/tar.gz-Archiv inkl. CSV-Meta-Tabelle, README und PDF-Übersicht.
- Rendert alle Flugtracks als **interaktive Leaflet-Karte** — direkt im Browser lokal nutzbar.

## Schnellstart

```bash
git clone https://github.com/Vollol1/igc-analyser.git
cd igc-analyser
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env mit DHV_XC_USERNAME, DHV_XC_PASSWORD und PILOT_NAME befüllen

./scripts/igc_extractor.py          # alle IGCs herunterladen & importieren
./scripts/export_igc_zip.py         # ZIP-Archiv erzeugen
./scripts/export_flight_map.py      # interaktive Karte erzeugen
cd data/export && python3 -m http.server 8000
```

Details stehen in der [README](README.md) und im [Quickstart-Runbook](docs/runbooks/quickstart.md).

## Highlights dieses Releases

- **Vollständige lokale Pipeline:** list → download → import → export → map in einem Tool.
- **Idempotenz & Resume:** unterbrochene Läufe können nahtlos fortgesetzt werden.
- **Interaktive Karte** mit Kategorie-Layern (XC / Höhenflug / Lokal), Startplatz-Markern, Popups und Statistik-Panel.
- **Strukturierter ZIP-/tar.gz-Export** mit README.txt, `export_meta.json`, `flights.csv`, `flight_summary.pdf` und benannten IGC-Dateien.
- **`.env`-basierte Konfiguration** inkl. `PILOT_NAME`, `DHV_XC_BASE_URL`, `DHV_XC_PILOT_ID` und optionalen Pfad-/Rate-Limit-Overrides.
- **Brand-neutrale Kommunikation** im Code und in der Doku.
- **Disclaimer beim Start** jeder Skript-Ausführung.

## Wichtiger Hinweis

`igc-extractor` ist ein **unabhängiges Community-Tool** und steht in **keiner Verbindung** zu dhv-xc.de, dem DHV oder dessen Serviceportal. Das Tool greift mit deinen persönlichen Credentials auf deine eigenen Daten zu.

**Nutzung auf eigene Gefahr:** Ein Account-Bann oder andere Sanktionen durch den Betreiber von dhv-xc.de sind nicht ausgeschlossen. Bitte verwende das Tool verantwortungsvoll, beachte Rate-Limits und starte keine parallelen Massenabfragen.

Die enthaltene IGC-Validierung ist rein **strukturell** (A-/B-/G-Records, Lesbarkeit). Eine kryptographische G-Record-Prüfung findet nicht statt.

## Systemanforderungen

- Python 3.10+
- `requests`, `beautifulsoup4`, `lxml`
- optional: `python-dotenv`, `tqdm`, `reportlab`

Siehe [`requirements.txt`](requirements.txt).

## Assets

- Quellcode (`.zip` / `.tar.gz`) — wird automatisch von GitHub/Gitea angehängt.

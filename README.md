# igc-extractor

Ein schlankes Python-CLI-Tool zum persönlichen Herunterladen von Paragliding-Flugtracks im IGC-Format von [dhv-xc.de](https://www.dhv-xc.de). Es wurde entwickelt, um die eigenen Flüge eines Piloten lokal, idempotent und reproduzierbar zu extrahieren, ohne externe Cloud-Dienste zu benötigen. Standardmäßig werden alle in `data/processed/flights.jsonl` vorhandenen Flüge verarbeitet; ein explizites Limit kann über `--flights N` gesetzt werden.

> **Schnellstart für neue Nutzer:** [`docs/runbooks/quickstart.md`](./docs/runbooks/quickstart.md) – eine Schritt-für-Schritt-Anleitung für Windows, macOS und Linux.

## Inhaltsverzeichnis

- [⚠️ Hinweis zur Nutzung](#hinweis-zur-nutzung)
- [Zweck](#zweck)
- [Ordnerstruktur](#ordnerstruktur)
- [Installation](#installation)
- [Aufrufbeispiele](#aufrufbeispiele)
  - [Hilfe anzeigen](#hilfe-anzeigen)
  - [Trockenlauf](#trockenlauf)
  - [Alle Flüge herunterladen](#alle-flüge-herunterladen)
  - [Nur die neuesten N Flüge herunterladen](#nur-die-neuesten-n-flüge-herunterladen)
  - [Lauf fortsetzen](#lauf-fortsetzen)
  - [Credentials über die Kommandozeile überschreiben](#credentials-über-die-kommandozeile-überschreiben)
  - [Flugliste als JSONL extrahieren](#flugliste-als-jsonl-extrahieren)
  - [IGC-Dateien als ZIP exportieren](#igc-dateien-als-zip-exportieren)
  - [Interaktive Karte exportieren](#interaktive-karte-exportieren)
- [Credentials / Secrets](#credentials--secrets)
- [Import & Validierung der heruntergeladenen Flüge](#import--validierung-der-heruntergeladenen-flüge)
  - [Was validiert wird](#was-validiert-wird)
  - [Ausgabe](#ausgabe)
- [Architekturentscheidungen](#architekturentscheidungen)
- [Agent-Verhalten und Dokumentation](#agent-verhalten-und-dokumentation)
- [Roadmap](#roadmap)

## ⚠️ Hinweis zur Nutzung

`igc-extractor` ist ein **inoffizielles, unabhängiges Community-Tool**. Es steht in **keiner Verbindung** zu [dhv-xc.de](https://www.dhv-xc.de), dem Deutschen Hängegleiterverband e.V. (DHV) oder dessen Serviceportal.

Das Tool meldet sich mit **deinen persönlichen dhv-xc.de-Zugangsdaten** an und lädt ausschließlich **deine eigenen IGC-Flugdateien** herunter. Es greift nicht auf fremde Accounts oder öffentliche Daten anderer Piloten zu.

**Nutzung auf eigene Gefahr:** Die öffentlich zugänglichen Nutzungsbedingungen von dhv-xc.de enthalten keine ausdrückliche Regelung zu automatisiertem Zugriff. Ein Account-Bann oder andere Sanktionen durch den Betreiber sind daher **nicht ausgeschlossen**. Bitte verwende das Tool verantwortungsvoll, setze Rate-Limits und starte keine parallelen Massenabfragen.

Bitte beachte stets die aktuellen Nutzungsbedingungen von dhv-xc.de:

- [dhv-xc.de Nutzungsvereinbarung](https://de.dhv-xc.de/info/nutzungsvereinbarung)
- [dhv-xc.de Release-Informationen](https://de.dhv-xc.de/info#relase-infos)

Weitere Hintergründe findest du in [ADR-003](./docs/decisions/ADR-003-public-release-dhv-xc.md) und [Legal & Release Notes](./docs/notes/legal-release-notes.md).

## Zweck

- Anmelden bei [dhv-xc.de](https://www.dhv-xc.de).
- Auslesen der Flugliste eines Piloten.
- Herunterladen der zugehörigen `.igc`-Dateien.
- Lokale Speicherung der Metadaten (SQLite/JSONL) für weitere Analysen.
- Wiederaufsetzbare Ausführung: bereits vorhandene Dateien werden nicht neu geladen, fehlgeschlagene Downloads können erneut versucht werden.

## Ordnerstruktur

```
igc-extractor/
├── data/
│   ├── igc/                  # Heruntergeladene .igc-Dateien
│   ├── processed/            # Generierte JSONL-Daten (z. B. flights.jsonl)
│   ├── export/               # Statische JSON-Exports
│   ├── logs/                 # Laufzeit-Logs und Summaries
│   ├── igc_extractor.db    # SQLite-Statusdatenbank des Downloaders (Resume / Idempotenz)
│   ├── igc-extractor.db      # SQLite-Analysedatenbank des Importers / Exporters
│   └── schema.sql            # SQLite-Schema für den Import
├── docs/
│   ├── decisions/            # Architecture Decision Records (ADRs)
│   ├── notes/                # Research notes (API, Pipeline, Kanban)
│   ├── runbooks/             # Schritt-für-Schritt-Anleitungen
│   ├── ROADMAP.md            # Geplante Releases und Features
│   └── TODO.md               # Lebendige Aufgabenliste
├── scripts/
│   ├── igc_extractor.py      # Orchestrierung: list → download → import
│   ├── list_flights.py       # Flugliste auslesen → JSONL
│   ├── download_igc.py       # IGC-Dateien herunterladen
│   ├── dhv_xc_client.py      # Authentifizierter HTTP-Client
│   ├── import_flights.py     # Import + Validierung in SQLite
│   ├── export_igc_zip.py     # Lokale IGC-Dateien als ZIP/TAR.GZ exportieren
│   └── export_flight_map.py  # Interaktive Leaflet-Karte erzeugen
├── .env.example              # Beispiel-Konfiguration (keine echten Werte)
├── .gitignore                # Ausschluss von .env, venv, Logs, DBs, IGCs …
├── requirements.txt          # Python-Abhängigkeiten
├── CHANGELOG.md              # Versionshistorie
├── AGENT_BEHAVIOR_NOTES.md   # Regeln für Agent-Sessions
└── README.md                 # Diese Datei
```

> **Hinweis:** Es gibt zwei SQLite-Datenbanken mit unterschiedlichen Zwecken:
> - `data/igc_extractor.db` wird vom Downloader als Resume-/Status-DB verwendet.
> - `data/igc-extractor.db` ist das Ziel von `import_flights.py` für Analysen/Exporte.
>
> Eine spätere Version kann die beiden Datenbanken zusammenführen (siehe `docs/ROADMAP.md`).

## Installation

1. Repository klonen:

   ```bash
   git clone https://github.com/Vollol1/igc-analyser.git
   cd igc-analyser
   ```

2. Virtuelles Environment anlegen und Abhängigkeiten installieren:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

   Benötigt werden mindestens `requests`, `beautifulsoup4` und `lxml`. `python-dotenv` und `tqdm` sind optional, aber für die bequeme `.env`-Workflow bzw. ansprechende Fortschrittsanzeigen empfohlen.

   Unter Windows verwende am besten **Git Bash**, damit die Befehle wie unter
   macOS/Linux funktionieren. Alternativ: `python -m venv venv` und
   `venv\Scripts\activate` in der Eingabeaufforderung. Siehe
   [`docs/runbooks/quickstart.md`](./docs/runbooks/quickstart.md) für details.

3. Konfigurationsdatei anlegen:

   ```bash
   cp .env.example .env
   # .env jetzt mit einem sicheren Editor bearbeiten
   ```

   In `.env` trägst du deine echten dhv-xc.de-Zugangsdaten ein:

   ```bash
   DHV_XC_USERNAME=dein_benutzername
   DHV_XC_PASSWORD=dein_passwort

   # Optional
   # DHV_XC_BASE_URL=https://www.dhv-xc.de
   # DHV_XC_PILOT_ID=12345
   ```

   > **Wichtig:** `.env` enthält echte Credentials und darf **niemals** in Git committet werden. Siehe [ADR-001](docs/decisions/ADR-001-architecture-techstack.md) und das Vorbild-Projekt [gag-atlas ADR-007](https://github.com/Vollol1/gag-atlas/blob/main/docs/decisions/ADR-007-secrets-management.md).

## Aufrufbeispiele

### Hilfe anzeigen

```bash
./scripts/igc_extractor.py --help
```

### Trockenlauf (zeigt, welche Flüge geladen würden)

```bash
./scripts/igc_extractor.py --flights 10 --dry-run
```

### Alle Flüge herunterladen (Default)

Ohne `--flights` verarbeitet `igc_extractor.py` alle in `data/processed/flights.jsonl` vorhandenen Flüge:

```bash
./scripts/igc_extractor.py
```

### Nur die neuesten N Flüge herunterladen

Das Limit bezieht sich immer auf die neuesten N Flüge der JSONL:

```bash
./scripts/igc_extractor.py --flights 200
```

### Lauf fortsetzen (bereits vorhandene Flüge überspringen)

```bash
./scripts/igc_extractor.py --resume
```

Mit explizitem Limit:

```bash
./scripts/igc_extractor.py --flights 200 --resume
```

### Credentials über die Kommandozeile überschreiben (nur für lokale Tests, nicht in Scripts/Skripten)

```bash
./scripts/igc_extractor.py \
  --username "$DHV_XC_USERNAME" \
  --password "$DHV_XC_PASSWORD" \
  --pilot-id 12345 \
  --flights 50
```

### Flugliste als JSONL extrahieren

```bash
./scripts/list_flights.py
```

Dieses Skript meldet sich an, liest mit den Filtern *Nur meine Flüge* / *Private
Flüge einschließen* alle eigenen Flüge aus und schreibt sie idempotent nach
`data/processed/flights.jsonl`. Pro Flug werden ID, Datum, Startplatz, Gleitschirm,
Best-Task-Distanz, Flugdauer und die IGC-Download-URL gespeichert. Läufe werden
nach `data/logs/list_flights_<run_id>.log` protokolliert.

### IGC-Dateien als ZIP exportieren

Nachdem Download und Import durchgelaufen sind, können alle lokalen IGC-Dateien
mit Metadaten und Validierungsstatus in ein ZIP- oder tar.gz-Archiv gepackt
werden:

```bash
./scripts/export_igc_zip.py
```

Das Archiv landet unter `data/export/igc_export_<run_id>.zip` (bzw. `*.tar.gz`) und enthält:

- `README.txt` – Deckblatt mit Piloten-/Absendername (Parameter `--pilot-name`
  / `--sender`), Erstellungsdatum, Anzahl Flüge, Zeitraum, Startorte und
  Hinweis zur strukturellen IGC-Validierung.
- `export_meta.json` – Übersicht (Anzahl Flüge, IGC-Dateien, Gesamtflugzeit,
  `sum_best_task_distance_km`, `best_single_flight_distance_km`,
  `best_single_flight`, Zeitraum, Startplätze, Erstellungsdatum,
  Validierungshinweis).
- `flights.csv` – Detaillierte Flugtabelle inkl. `IDFlight`, `FlightDate`,
  `TakeoffLocation`, `Glider`, `FlightDuration`, `BestTaskDistanceKm`,
  `IgcFilenameInArchive`, `ValidStatus` und `OriginalIgcFilename` (sofern in
  der Datenbank vorhanden).
- `flight_summary.pdf` – Strukturierte deutsche Zusammenfassung mit Deckblatt,
  kompakter Meta-Tabelle, Validierungshinweis und tabellarischer Flugliste im
  Querformat; generiert mit `reportlab>=4.0.0` (siehe ADR-002).
- `<IDFlight>_<FlightDate>_<TakeoffLocation>.igc` – Die IGC-Dateien mit
  sprechenden Dateinamen.

Optionale Parameter:

- `--pilot-name "Max Mustermann"` – Name für das Deckblatt `README.txt`.
  `--sender` ist ein Alias. Standardmäßig wird die Umgebungsvariable `PILOT_NAME`
  verwendet; wenn diese nicht gesetzt ist, erscheint ein neutraler Platzhalter.
- `--output-dir data/export` – Zielverzeichnis für das Archiv.
- `--igc-dir data/igc` – Verzeichnis mit den lokalen IGC-Dateien.
- `--flights-jsonl data/processed/flights.jsonl` – Quelle der Flugmetadaten.
- `--db data/igc-extractor.db` – SQLite-DB für den Validierungsstatus.
- `--output-name mein_export.zip` – Expliziter Archivname.
- `--format tar.gz` – Alternativ ein tar.gz-Archiv erzeugen.

Details und eine Schritt-für-Schritt-Anleitung stehen im
[IGC-Export-Runbook](docs/runbooks/export-igc.md).

### Interaktive Karte exportieren

Nachdem Flugmetadaten und IGC-Dateien vorliegen, kannst du eine interaktive
Leaflet-Karte mit allen Tracks, Startplatz-Markern, Popups und einem
Statistik-Panel erzeugen:

```bash
./scripts/export_flight_map.py
```

Das erzeugt `data/export/flights_map_<run_id>.html` mit OpenStreetMap-Hintergrund.
Über das Layer-Control lässt sich zwischen den Gruppierungen Kategorie
(Default: Lokal / XC / Höhenflug), Startplatz, Flugjahr und Gleitschirm
umschalten. Details und weitere Aufrufbeispiele stehen im
[Karten-Export-Runbook](docs/runbooks/export-flight-map.md).

> **Tipp:** Die Karte lässt sich lokal öffnen, indem du die generierte HTML-Datei direkt im Browser aufrufst (z. B. per Doppelklick auf `data/export/flights_map_<run_id>.html`). Für eine zuverlässige Darstellung der externen Kartenkacheln kannst du alternativ einen kleinen lokalen Server starten:
>
> ```bash
> cd data/export
> python -m http.server 8000
> ```
>
> Anschließend ist die Karte unter `http://localhost:8000/flights_map_<run_id>.html` erreichbar.

## Credentials / Secrets

Credentials werden in dieser Reihenfolge aufgelöst (erste Treffer gewinnt):

1. Kommandozeilenargumente (`--username`, `--password`, `--pilot-id`, `--base-url`).
2. Umgebungsvariablen (`DHV_XC_USERNAME`, `DHV_XC_PASSWORD`, `DHV_XC_BASE_URL`, `DHV_XC_PILOT_ID`).
3. Aus `.env`, sofern `python-dotenv` installiert ist.

- Committe niemals `.env`.
- Schreibe keine Passwörter direkt in Python-Dateien oder Shell-Skripte.
- Sollte ein Secret unbeabsichtigt in die Git-History gelangen: Key sofort rotieren und die History bereinigen (siehe gag-atlas ADR-007).

## Import & Validierung der heruntergeladenen Flüge

Nachdem die `.igc`-Dateien und `flights.jsonl` vorliegen (z. B. durch den Downloader erzeugt), werden sie mit `scripts/import_flights.py` in eine SQLite-Datenbank importiert und minimal validiert.

```bash
./scripts/import_flights.py
```

Standardpfade:

- Eingabe: `data/processed/flights.jsonl`
- IGC-Dateien: `data/igc/`
- SQLite-DB: `data/igc-extractor.db`
- Schema: `data/schema.sql`
- JSON-Export: `data/export/flights_overview.json`
- Log: `data/logs/import_flights_<run_id>.log`

### Was validiert wird

`import_flights.py` führt eine **strukturelle Minimalvalidierung** durch:

- A-Record (Hersteller-/Seriennummer) muss am Dateianfang stehen.
- Es muss mindestens ein B-Record (Positionsfix) vorhanden sein.
- Eine G-Record-Zeile muss am Dateiende stehen.
- Die Datei muss lesbarer UTF-8-Text sein und eine Mindestgröße überschreiten (50 Byte).

Jeder Flug erhält den Status `valid`, `invalid` oder `missing`.  
**Hinweis:** Die kryptographische Prüfung der G-Record-Signatur wird **nicht** durchgeführt.

### Ausgabe

Die SQLite-Datenbank enthält die Tabellen:

- `flights` – Flugmetadaten, Hash und Validierungsstatus.
- `flight_stats` – eine Zeile pro Lauf mit `total`, `valid`, `invalid`, `missing`, `downloaded`.

Zusätzlich wird `data/export/flights_overview.json` mit der Zusammenfassung geschrieben (vergleichbar zu einem statischen Export im gag-atlas-Projekt).

## Architekturentscheidungen

Die wichtigsten Entscheidungen sind in [docs/decisions/ADR-001-architecture-techstack.md](docs/decisions/ADR-001-architecture-techstack.md) festgehalten:

- **Python + Requests/BeautifulSoup**: schlank, portabel, keine schwere Framework-Abhängigkeit.
- **Lokale SQLite/JSONL**: keine externe Datenbank nötig.
- **Idempotenz & Resume**: gleiche Eingabe führt bei wiederholtem Lauf zum gleichen Ergebnis; unterbrochene Läufe können nahtlos fortgesetzt werden.
- **`.env`-basierte Secrets**: Credentials ausschließlich über Umgebungsvariablen / `.env`, niemals im Code.

Weitere Architektur-Entscheidungen folgen im Verzeichnis [docs/decisions/](docs/decisions/).

## Agent-Verhalten und Dokumentation

Für jede Agent-Session gelten die Regeln in [`AGENT_BEHAVIOR_NOTES.md`](./AGENT_BEHAVIOR_NOTES.md).  
Die wichtigsten Dokumentationsbereiche sind:

- [`docs/decisions/`](./docs/decisions/) — Architecture Decision Records (ADRs)
- [`docs/notes/`](./docs/notes/) — Session-Learnings, API-Beobachtungen, Pipeline-Notizen
- [`docs/runbooks/`](./docs/runbooks/) — Schritt-für-Schritt-Anleitungen, z. B. IGC-Download
- [`docs/TODO.md`](./docs/TODO.md) — Lebendige Aufgabenliste
- [`docs/ROADMAP.md`](./docs/ROADMAP.md) — Geplante Releases und kommende Features

Wichtige Regeln auf einen Blick:

1. Vor jedem Commit `docs/decisions/`, `docs/notes/` und `docs/TODO.md` prüfen/aktualisieren.
2. Technische Entscheidungen als ADR festhalten.
3. Session-Learnings in `docs/notes/` dokumentieren.
4. `docs/TODO.md` lebendig halten.
5. Agent-Änderungen nur im Worktree; Merge passiert durch Kanban-Workflow.
6. Lange Tasks nicht im Agent blockieren; stattdessen Hintergrundprozesse + Resume/Logs.
7. Tests grün vor Commit (wenn Tests existieren — aktuell gibt es noch kein `tests/`-Verzeichnis, siehe `AGENT_BEHAVIOR_NOTES.md`).
8. Kanban-Sidebar-Agent darf Worktree-Ergebnisse ins Haupt-Repo übernehmen, wenn Auto-Review fehlschlägt.
9. Auto-Review für Datei-erstellende Tasks: `--auto-review-enabled true --auto-review-mode commit` setzen.
10. Wiederkehrende Muster in `AGENT_BEHAVIOR_NOTES.md` dokumentieren.

## Roadmap

Die geplante Weiterentwicklung ist in [`docs/ROADMAP.md`](./docs/ROADMAP.md) festgehalten.  
Die nächsten Meilensteine umfassen IGC-Export für Höhenflugnachweise, Kartenvisualisierung, Import aus weiteren Quellen sowie Deduplizierung/Konsistenzprüfung.

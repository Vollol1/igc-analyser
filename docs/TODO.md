# igc-extractor TODO

Lebendige Aufgabenliste für den igc-extractor. Diese Datei liegt im Repository, damit sie über Kanban-Resets und Agent-Session-Neustarts hinweg erhalten bleibt.

Langfristige Releases und Feature-Zuordnungen sind in [`docs/ROADMAP.md`](./ROADMAP.md) beschrieben.

> **Hinweis:** Prozessregel nach Worktree-Verlust angepasst — siehe [AGENT_BEHAVIOR_NOTES.md](../AGENT_BEHAVIOR_NOTES.md) Regel 13 und [docs/notes/worktree-loss-incident-2026-08-17.md](./notes/worktree-loss-incident-2026-08-17.md).

## Status-Legende

- `[ ]` offen
- `[-]` in Arbeit
- `[x]` erledigt
- `[?]` optional / zurückgestellt
- `[!]` blockiert

## Aktuell in Arbeit

- [x] Öffentlicher GitHub-Release v1.0.0 vorbereiten: ADR-003 + Legal Notes + README/Tool-Disclaimer
  - Recherche der öffentlichen dhv-xc.de-Quellen (`Nutzungsvereinbarung`, `Release-Informationen`).
  - Dokumentation in [`docs/notes/legal-release-notes.md`](./notes/legal-release-notes.md).
  - Architekturentscheidung in [`docs/decisions/ADR-003-public-release-dhv-xc.md`](./decisions/ADR-003-public-release-dhv-xc.md).
  - Vorgeschlagene Disclaimer-Texte für README und Tool-Output in ADR-003 und Legal Notes hinterlegt.
  - Code bereinigt:
    - Persönliche Defaults (`Florian Knab`) aus `export_flight_map.py` und `export_igc_zip.py` entfernt.
    - Pilotenname wird aus `PILOT_NAME`-Umgebungsvariable gelesen, per `--pilot-name` überschrieben; leer = generischer Platzhalter.
    - Absolute Pfade (`/home/florian/...`) aus `igc_extractor.py`, `.env.example`, `.gitignore` entfernt; ADR-007-Verweis auf relativen Pfad bzw. öffentlichen GitHub-Mirror geändert.
    - Brand-Neutralität: Docstrings/CLI-Descriptions auf "supported flight-data platform" umgestellt.
    - Disclaimer-Output beim Startup in `igc_extractor.py`, `list_flights.py`, `download_igc.py` hinzugefügt (non-blocking, ausgenommen `--help` bzw. `--dry-run` bei `igc_extractor.py`).
  - Dokumentation finalisiert:
    - `README.md` mit Disclaimer, Quickstart-Link und neutraler GitHub-Klon-URL aktualisiert.
    - `docs/runbooks/quickstart.md` als systemübergreifende, einsteigerfreie Anleitung erstellt.
    - Bestehende Runbooks (`download-igc.md`, `export-flight-map.md`, `export-igc.md`) auf portable Befehle umgestellt; absolute Pfade und persönliche Namen entfernt.
    - `PILOT_NAME=""` in `.env.example` dokumentiert und `PILOT_NAME`-Default-Dokumentation in Runbooks korrigiert.
    - `docs/TODO.md` und `CHANGELOG.md` aktualisiert.
  - CI-Grundgerüst erstellt: `.github/workflows/ci.yml`.
  - `docs/ROADMAP.md` für v1.0.0 aktualisiert.
  - Release-Draft erstellt: `docs/notes/github-release-draft.md`.

- [x] Bugfix: `scripts/igc_extractor.py` verwendet `project_root()` korrekt
  - Fehler: `TypeError: unsupported operand type(s) for /: 'function' and 'str'`
    nach erfolgreichem `list_flights.py`-Lauf.
  - Ursache: `common.project_root` ist eine Funktion, wurde aber an mehreren
    Stellen in `igc_extractor.py` ohne `()` als `Path`-Objekt verwendet.
  - Fix: Alle Stellen auf `root = project_root()` umgestellt; Parameter
    `project_root: Path` in `_run_subprocess`, `_run_list_flights`,
    `_run_download_igc`, `_run_import_flights` in `root: Path` umbenannt.
  - Dokumentiert in [`docs/notes/igc-extractor-project-root-bugfix-2026-08-18.md`](./notes/igc-extractor-project-root-bugfix-2026-08-18.md).
  - Validierung: `python3 -m py_compile scripts/igc_extractor.py` und
    `./scripts/igc_extractor.py --help` erfolgreich.

- [x] Kartenfeature vorbereiten/umsetzen — Teil 1 erledigt
  - Anforderungen dokumentiert in [`docs/notes/flight-map-requirements.md`](./notes/flight-map-requirements.md).
  - Gemeinsames Hilfsmodul `scripts/common.py` angelegt.
  - Duplizierte Hilfsfunktionen aus `list_flights.py`, `download_igc.py`,
    `igc_extractor.py`, `import_flights.py` und `export_igc_zip.py` in
    `common.py` extrahiert.
  - Refactoring dokumentiert in [`docs/notes/common-refactoring.md`](./notes/common-refactoring.md).
  - Nächster Schritt: `scripts/export_flight_map.py` implementieren.

- [x] Default-Limit von `--flights` in `scripts/igc_extractor.py` entfernen
  - Problem: Default `200` führte dazu, dass bei 306 Flügen nur 200 verarbeitet
    wurden; 106 ältere Flüge wurden ignoriert.
  - Lösung: `--flights` hat jetzt default `None`, d. h. alle Flüge in
    `data/processed/flights.jsonl` werden verarbeitet. Ein Limit muss explizit
    mit `--flights N` gesetzt werden.
  - `_prepare_download_subset` und `_print_dry_run_preview` behandeln `limit=None`
    korrekt.
  - `README.md` und `docs/runbooks/download-igc.md` dokumentieren das neue
    Default-Verhalten und explizite Limits.

## Erledigt

- [x] v0.2.1 Patch-Release
  - Bugfix: `scripts/igc_extractor.py` übergibt `import_flights.py` jetzt `data/igc-extractor.db` statt der State-DB.
  - Dokumentation korrigiert (`README.md`, `docs/runbooks/download-igc.md`).
  - Datenbank-Incident dokumentiert (`docs/notes/pipeline-notes.md`).
  - `CHANGELOG.md` und `docs/ROADMAP.md` für v0.2.1 aktualisiert.

## Kurzfristig geplant

_(verschoben aus dem ursprünglichen v0.2.0-Scope; siehe [ROADMAP.md](./ROADMAP.md) [Unreleased] / Nächstes Release)_

- [ ] Testsuite aufbauen (`tests/`)
  - Unit-Tests für IGC-Validierung, Dateinamensgenerierung und Hash-Bildung.
  - Integrationstest mit lokalen Mock-IGC-Dateien (kein Netzwerkaufruf).
  - CI-fähig machen, sobald mindestens eine grundlegende Testsuite existiert.
- [ ] Resume-Logik für fehlgeschlagene Downloads verbessern
  - `attempts`-Zähler in der Downloader-State-DB (`data/igc_extractor.db`) führen.
  - Dauerhaft fehlgeschlagene Flüge erkennen und ausgeben, statt sie endlos zu wiederholen.
- [ ] Zwei SQLite-Datenbanken konsolidieren
  - Aktuell: `data/igc_extractor.db` (Downloader-Resume) und `data/igc-extractor.db` (Import/Analyse).
  - Langfristig eine einzige DB anstreben; Schritte und Migration in ADR festhalten.
- [ ] `LandingLocation` aus DHV-XC Detailseite scrapen und in Export aufnehmen
  - Die Flugliste (`/flights?mine=1&incpriv=1`) liefert `LandingLocation` nicht.
  - Auf der Detailseite (`/flight/<IDFlight>`) ist `LandingLocation` im
    JavaScript-Block `kers.app.fli.handler.init(...)` verfügbar.
  - Erfordert einen zusätzlichen HTTP-Request pro Flug sowie Retry-/Rate-Limit-Logik.
- [ ] Validierungs- und Ausreißer-Checks für Flugdaten
  - Längster Flug / maximale Distanz können laut Benutzer-Feedback nicht stimmen – Track hat Fehler.
  - Plausibilitätsprüfung für Distanz, Flugzeit und Höhenmeter einführen.
  - Auffällige Flüge in `flights.csv`/Datenbank markieren oder in separates Protokoll ausgeben.
- [x] Kartenfeature: Schritte für `scripts/export_flight_map.py` (v0.3.0)
  - Utilities extrahieren (wiederverwendbarer B-Record-Parser, ggf. gemeinsame Flug-Metadaten-Leser).
  - [x] Basis-Karte mit Kategorie-Layer (Lokal / XC / Höhenflug).
  - [x] Zusätzliche Gruppierungen (Startplatz, Flugjahr, Gleitschirm).
  - SVG/PNG-Export der Karte (optional, v1.1.0).
  - 3D-Ansicht der Tracks (optional, später).

## Erledigt

- [x] `scripts/download_igc.py` repariert und erweitert
  - Liest das JSONL-Schema von `list_flights.py` (`IDFlight`, `FlightDate`, `TakeoffLocation`, `IgcUrl`).
  - Verwendet den gemeinsamen `DhvXcClient` (`scripts/dhv_xc_client.py`) mit Session-/CSRF-/PHPSESSID-Login statt HTTP-Basic-Auth.
  - Rate-Limiting (`--rate-limit`) und Retry-Logik (`--max-retries`) implementiert.
  - Unterstützt `--offset` und `--limit` für stückweise/batchweise Downloads.
  - Logs/Summaries werden nach `data/logs/` geschrieben.
- [x] Gemeinsames `scripts/dhv_xc_client.py` aus `list_flights.py` extrahiert
  - Zentraler authentifizierter Client für Login, Flugliste und IGC-Download.
- [x] `scripts/igc_extractor.py` erweitert
  - `--rate-limit`, `--max-retries`, `--batch-size`, `--batch-pause` werden an `download_igc.py` weitergegeben.
  - Download läuft intern in Batches mit Re-Login und Pause zwischen den Batches.
  - Führt nach Download automatisch `import_flights.py` aus.
- [x] `scripts/import_flights.py` erstellt
  - Importiert `flights.jsonl` + IGC-Dateien in `data/igc-extractor.db`.
  - Führt strukturelle Minimalvalidierung durch (A/B/G-Records, Größe, UTF-8).
  - Erzeugt `data/export/flights_overview.json`.
- [x] `scripts/export_igc_zip.py` erstellt
  - Packt lokale IGC-Dateien aus `data/igc/` in ein ZIP-Archiv nach `data/export/igc_export_<run_id>.zip`.
  - Benennt Dateien im Archiv als `<IDFlight>_<FlightDate>_<TakeoffLocation>.igc`.
  - Schreibt `export_meta.json` (Übersichtsstatistik) und `flights.csv` (Flugtabelle inkl. Valid-Status) ganz oben in das Archiv.
  - Unterstützt `--format zip` und `--format tar.gz`.
  - Log nach `data/logs/export_igc_zip_<run_id>.log`, Summary nach `data/logs/export_igc_zip_summary_<run_id>.json`.
- [x] Login-Mechanismus dokumentieren und robust gegen Token-/Layout-Änderungen machen
- [x] Rate-Limiting / Retry-Logik für Downloads ergänzen
- [x] IGC-Validierung korrigiert und dokumentiert
  - G-Record muss nach dem letzten B-Record liegen, nicht zwingend als letzte Zeile der Datei (Naviter-Logger hängen `LX*` Endinfo-Datensätze nach dem G-Record an).
- [x] Dokumentations- und Agent-Verhaltens-Struktur aus gag-atlas übernommen
  - `AGENT_BEHAVIOR_NOTES.md` im Repo-Root erstellt.
  - `docs/notes/kanban-notes.md` mit Workflow-Beobachtungen erstellt.
  - `docs/notes/pipeline-notes.md` für IGC-Download/Import-Beobachtungen erstellt.
  - `docs/notes/dhv-xc-api.md` mit API-/Login-Analyse erstellt.
  - `docs/runbooks/download-igc.md` mit Schritt-für-Schritt-Anleitung erstellt.
  - `docs/decisions/ADR-001-architecture-techstack.md` auf neues docs-Schema aktualisiert.
  - `README.md` verlinkt `AGENT_BEHAVIOR_NOTES.md` und die wichtigsten docs/-Unterverzeichnisse.
- [x] Vollständige Pipeline aus Flugliste → Download → Import → Export automatisiert testen
  - Echter End-to-End-Lauf am 29.07.2026 mit 288 eigenen Flügen: 288/288 IGC-Dateien heruntergeladen, 287/288 valid, 1 invalid (Flug 2234459 ohne G-Record).
- [x] Datenqualität der importierten Flüge über Stichproben evaluieren
  - Stichprobe zeigt: Naviter-Logger hängen `LX*` Endinfo-Datensätze nach dem G-Record an; daher wurde die Validierung angepasst.

## Mittelfristig geplant

- [ ] Datenqualität weiterhin gelegentlich prüfen (z. B. nach jedem größeren Download).
- [x] IGC-Export-Archiv als Basis für Nachweise (v0.2.0)
  - `scripts/export_igc_zip.py` erstellt ein ZIP/tar.gz-Archiv mit `README.txt`, `export_meta.json`, `flights.csv`, `flight_summary.pdf` und den IGC-Dateien.
  - `README.txt` enthält den Piloten-/Absendernamen (Parameter `--pilot-name` / `--sender`).
  - `flight_summary.pdf` enthält ein strukturiertes Deckblatt (Pilot, Zeitraum, Anzahl Flüge, IGC-Dateien, Gesamtflugzeit, XC-Distanz, bester Flug, Startorte, Erstellungsdatum, Hinweis zur Validierung) sowie eine tabellarische Übersicht aller Flüge.
  - PDF-Generierung über `reportlab>=4.0.0` (reiner Python, keine externen System-Dependencies); siehe [ADR-002](../decisions/ADR-002-pdf-reporting-reportlab.md).
  - Generierte Archive stehen in `.gitignore`.
  - Der vollständige Höhenflug-Nachweis (Filter nach Mindesthöhe, dedizierte Views) ist zurückgestellt; siehe `docs/ROADMAP.md` [Unreleased] / Optional.
  - Siehe auch [`docs/runbooks/export-igc.md`](../runbooks/export-igc.md).
- [ ] `LandingLocation` aus DHV-XC Detailseite scrapen und in Export aufnehmen
  - Die Flugliste (`/flights?mine=1&incpriv=1`) liefert `LandingLocation` nicht.
  - Auf der Detailseite (`/flight/<IDFlight>`) ist `LandingLocation` im
    JavaScript-Block `kers.app.fli.handler.init(...)` verfügbar.
  - Erfordert einen zusätzlichen HTTP-Request pro Flug sowie Retry-/Rate-Limit-Logik.
- [ ] Validierungs- und Ausreisser-Checks für Flugdaten
  - Längster Flug / maximale Distanz können laut Benutzer-Feedback nicht stimmen – Track hat Fehler.
  - Plausibilitätsprüfung für Distanz, Flugzeit und Höhenmeter einführen.
  - Auffällige Flüge in `flights.csv`/Datenbank markieren oder in separates Protokoll ausgeben.

## Abgeschlossen

_(keine außerhalb von "Erledigt")_

## Optional / Zurückgestellt

- [?] Web-Frontend oder Visualisierung für heruntergeladene Flüge (wird in ROADMAP v1.1.0 betrachtet)
- [?] Cloud-Fallback für dhv-xc.de (aktuell nicht vorgesehen)

## Langfristig / Vision

- [ ] IGC-Download- und Import-Pipeline vollständig ohne manuelle Worktree-Intervention ausführbar.
- [ ] Alle gewünschten Flüge lokal vorhanden, validiert und in SQLite importiert.
- [x] Interaktive Kartenvisualisierung der importierten Flüge (v0.3.0)
- [?] Höhenflug-Nachweis (dedizierter Export/Filter nach Mindesthöhe) (zurückgestellt)
- [?] Erweiterte Kartenvisualisierung (SVG/PNG-Export, Heatmap, 3D) (v1.1.0)
- [ ] Import aus weiteren Quellen (z. B. XContest, XCTrack, lokale Logger-Dateien) (v1.1.0)
- [ ] Deduplizierung und Konsistenzprüfung über alle importierten Flüge hinweg (v1.2.0)
- [ ] Testsuite und CI für zuverlässige Releases (siehe Kurzfristig geplant)

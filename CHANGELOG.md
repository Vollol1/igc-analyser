# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Public-release cleanup:
  - Removed personal default pilot name (`Florian Knab`) from `scripts/export_flight_map.py` and `scripts/export_igc_zip.py`.
  - Pilot/sender name is now read from the `PILOT_NAME` environment variable and can be overridden via `--pilot-name` (or `--sender` in `export_igc_zip.py`). If unset, a generic placeholder is used.
  - Replaced absolute local paths (`/home/florian/...`) in `scripts/igc_extractor.py`, `.env.example`, and `.gitignore` with relative documentation references or a public GitHub mirror link.
  - Made CLI descriptions and docstrings brand-neutral: they now refer to a "supported flight-data platform" instead of naming the platform.

### Added
- Non-blocking startup disclaimer in `scripts/igc_extractor.py`, `scripts/list_flights.py`, and `scripts/download_igc.py`:
  - Warns that the tool accesses a flight-data platform with user credentials, that usage is at the user's own risk, and that account bans or other sanctions are possible.
  - Skipped when `--help` is used; in `igc_extractor.py` also skipped during `--dry-run`.
- `PILOT_NAME=""` documented in `.env.example` with usage notes for `export_igc_zip.py` and `export_flight_map.py`.

## [0.3.0] - 2026-08-18

### Added
- `scripts/export_flight_map.py` — Interaktive Leaflet-Karte zur Visualisierung aller importierten Flüge:
  - Flugtracks als farbige Polylinien, kategorisiert nach XC / Höhenflug / Lokal.
  - Startplatz-Marker mit Tooltips und Popups.
  - Statistik-Panel mit Fluganzahl, Zeitraum, Gesamtflugzeit, XC-Distanz, bestem Flug, Startplätzen, Gleitschirmen und Validierungsstatus.
  - Zusätzliche Layer-Gruppen: Startplatz, Flugjahr, Gleitschirm.
  - Zoom-abhängige Linienstärke für bessere Sichtbarkeit bei jedem Zoom-Level.
  - Ein-/ausklappbares Statistik-Panel mit Toggle-Button.
  - Flug-Highlighting: Klick/Hover auf Tracks zeigt Meta-Infos (Datum, Distanz, Dauer, max. Höhe, Startplatz, Gleitschirm, Status) in einem separaten Info-Panel.
  - Outlier-Erkennung filtert fehlerhafte B-Records (z. B. 0,0-Koordinaten, Sprünge > 100 km) und markiert betroffene Flüge im Popup.
  - Ausgabe: `data/export/flights_map_<run_id>.html` mit Log und JSON-Summary unter `data/logs/`.
- `docs/notes/flight-map-requirements.md` — Anforderungen und Design-Entscheidungen für die Kartenvisualisierung.
- `docs/notes/session-status-2026-08-18.md` — Session-Notizen zu Kartenfeature-Iterationen und Bugfixes.

### Changed
- `scripts/export_flight_map.py` verwendet zoom-abhängige Linienstärke (1.4–5) statt fester Stärke.
- Kategorie-Zählung im Statistik-Panel basiert nur auf Flügen mit vorhandenem Track (konsistent mit Layer-Control).
- Marker-Design dezenter angepasst (Radius 3, fillOpacity 0.7) für bessere Track-Sichtbarkeit.

### Fixed
- Bugfix: `--flights` Parameter in `scripts/igc_extractor.py` hat standardmäßig nur 200 Flüge verarbeitet. Default ist jetzt `None` (alle Flüge). Explizites Limit muss mit `--flights N` gesetzt werden.
- Tile-Layer von OpenStreetMap auf CartoDB Positron gewechselt (vermeidet 403-Fehler bei `file://`-Nutzung).
- Statistik-Panel ist jetzt scrollbar (`max-height: 50vh`) und überlappt nicht mehr den Viewport.
- Layer-Control nach links oben verschoben und z-Index erhöht, um Überlappungen zu vermeiden.

### Notes
- 106 von 306 Flügen hatten zum Zeitpunkt der Entwicklung keine lokale IGC-Datei. Nach Ausführen von `./scripts/igc_extractor.py` (mit neuem Default ohne Limit) werden alle fehlenden IGCs nachgeladen.
- 6 Flüge enthielten outlier-Punkte (insgesamt 83), die automatisch gefiltert und im Popup markiert werden.

## [0.2.1] - 2026-08-17

### Fixed
- `scripts/igc_extractor.py` now passes `import_flights.py` the analysis database `data/igc-extractor.db` via `--db`, instead of the downloader state database `data/igc_extractor.db`. The `--state-db` parameter continues to control the downloader/resume database. This ensures validation status written by `import_flights.py` is visible to `export_igc_zip.py`.
- Corrected documentation references in `README.md` and `docs/runbooks/download-igc.md` to show `data/igc-extractor.db` as the import/analysis database.

### Notes
- Documented cleanup of the `flights`/`flight_stats` tables that had accidentally been created in `data/igc_extractor.db`. 18 missing flights were migrated to `data/igc-extractor.db`; the erroneous tables were then dropped from the state database. See `docs/notes/pipeline-notes.md`.

## [0.2.0] - 2026-08-16

### Added
- `scripts/export_igc_zip.py` — export downloaded IGC files as structured `*.zip` or `*.tar.gz` archives under `data/export/`:
  - `README.txt` cover sheet with pilot/sender name (configurable via `--pilot-name` / `--sender` or the `PILOT_NAME` environment variable), archive contents, validation notes and creation date.
  - `export_meta.json` archive overview: total flights, IGC files, summed flight duration, `sum_best_task_distance_km`, `best_single_flight_distance_km`, `best_single_flight` (ID, date, takeoff, glider), period, unique takeoff locations and generation timestamp.
  - `flights.csv` detailed flight table including `IDFlight`, `FlightDate`, `TakeoffLocation`, `Glider`, `FlightDuration`, `BestTaskDistanceKm`, `IgcFilenameInArchive`, `ValidStatus` and `OriginalIgcFilename`.
  - `flight_summary.pdf` structured German flight summary (cover page, compact meta table, validation note and landscape flight table) generated with `reportlab>=4.0.0`; see ADR-002.
  - IGC files inside the archive use speaking names: `<IDFlight>_<FlightDate>_<TakeoffLocation>.igc`.
  - Run log and JSON summary are written under `data/logs/`.
- `docs/decisions/ADR-002-pdf-reporting-reportlab.md` documenting the PDF-generation decision.
- `docs/ROADMAP.md` with planned releases v0.2.0–v0.5.0.

### Changed
- Consolidated and cleaned up project documentation (`README.md`, `docs/TODO.md`, agent notes, pipeline notes, runbooks).
- Documented known inconsistencies such as the two SQLite database names and the missing `tests/` folder.
- Corrected the meta distance fields in `export_meta.json`:
  - Renamed `total_best_task_distance_km` to `sum_best_task_distance_km` to clarify it is the sum of all Best-Task-Distances.
  - Added `best_single_flight_distance_km` (max Best-Task-Distance of a single flight).
  - Added `best_single_flight` with `IDFlight`, `FlightDate`, `TakeoffLocation` and `Glider` of the best flight.
  - Updated `README.txt` and `docs/runbooks/export-igc.md` accordingly.

### Removed
- `LandingLocation` from the CSV / archive export. The list view used by `list_flights.py` does not provide this field; future releases may scrape it from individual flight detail pages.

## [0.1.0] - 2026-07-29

### Added
- Authenticated login to a supported flight-data platform (default: [dhv-xc.de](https://www.dhv-xc.de)) via shared `DhvXcClient` (`scripts/dhv_xc_client.py`).
- `scripts/list_flights.py` – list own flights (including private flights) and write them to `data/processed/flights.jsonl`.
- `scripts/download_igc.py` – download IGC files in batches with rate limiting, retries, and resume support.
- `scripts/import_flights.py` – import flight metadata and downloaded IGC files into SQLite with structural validation.
- `scripts/igc_extractor.py` – orchestrator CLI that runs the full pipeline: list → download → import.
- Structural IGC validation (A/B/G records, size, readability) without cryptographic G-Record verification.
- Local SQLite/JSONL storage, idempotent execution, and resume support.
- `.env`-based credential handling; credentials never committed.
- Documentation: README, ADR-001, runbooks, API notes, pipeline notes, agent behavior notes.

### Verified Result
- 288 own flights found on dhv-xc.de.
- 288 IGC files downloaded to `data/igc/`.
- 287 valid, 1 invalid (missing G-Record), 0 missing.

[0.3.0]: ../igc-extractor/releases/tag/v0.3.0
[0.2.1]: ../igc-extractor/releases/tag/v0.2.1
[0.2.0]: ../Vollol1/igc-extractor/releases/tag/v0.2.0
[0.1.0]: ../igc-extractor/releases/tag/v0.1.0

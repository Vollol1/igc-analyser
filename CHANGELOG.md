# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- `scripts/igc_extractor.py` now passes `import_flights.py` the analysis database `data/igc-extractor.db` via `--db`, instead of the downloader state database `data/igc_extractor.db`. The `--state-db` parameter continues to control the downloader/resume database. This ensures validation status written by `import_flights.py` is visible to `export_igc_zip.py`.

## [0.2.0] - 2026-08-16

### Added
- `scripts/export_igc_zip.py` — export downloaded IGC files as structured `*.zip` or `*.tar.gz` archives under `data/export/`:
  - `README.txt` cover sheet with pilot/sender name (default `Florian Knab`, configurable via `--pilot-name` / `--sender`), archive contents, validation notes and creation date.
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
- Authenticated login to [dhv-xc.de](https://www.dhv-xc.de) via shared `DhvXcClient` (`scripts/dhv_xc_client.py`).
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

[0.2.0]: https://github.com/Vollol1/igc-extractor/releases/tag/v0.2.0
[0.1.0]: https://github.com/Vollol1/igc-extractor/releases/tag/v0.1.0

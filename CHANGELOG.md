# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `docs/ROADMAP.md` with planned releases v0.2.0–v0.5.0.

### Changed
- Consolidated and cleaned up project documentation (`README.md`, `docs/TODO.md`, agent notes, pipeline notes).
- Documented known inconsistencies such as the two SQLite database names and the missing `tests/` folder.

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

[0.1.0]: https://github.com/Vollol1/igc-extractor/releases/tag/v0.1.0

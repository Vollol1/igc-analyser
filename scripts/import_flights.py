#!/usr/bin/env python3
"""
Import flight metadata and downloaded IGC files into SQLite.

This script reads `flights.jsonl` and the matching files from `data/igc/`,
calculates MD5/SHA256 hashes, performs a minimal structural IGC validation,
and stores the results in `data/igc-extractor.db`.

The validation is intentionally lightweight:
- A-Record (manufacturer / serial) must be present at the beginning.
- At least one B-Record (fix) must be present.
- A G-Record must be present at the end of the file.
- File must exceed a minimum size (50 bytes) and be readable as text.

This is NOT a full G-Record cryptographic validation. It only catches
corrupt, empty, truncated or otherwise obviously broken IGC files.
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FLIGHTS_JSONL = PROJECT_ROOT / "data" / "processed" / "flights.jsonl"
DEFAULT_IGC_DIR = PROJECT_ROOT / "data" / "igc"
DEFAULT_DB = PROJECT_ROOT / "data" / "igc-extractor.db"
DEFAULT_SCHEMA = PROJECT_ROOT / "data" / "schema.sql"
DEFAULT_EXPORT_DIR = PROJECT_ROOT / "data" / "export"
DEFAULT_LOG_DIR = PROJECT_ROOT / "data" / "logs"
MIN_IGC_SIZE = 50


def setup_logging(run_id: str, log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"import_flights_{run_id}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, mode="w", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return log_path


def generate_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Flights JSONL not found: {path}")
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                records.append(json.loads(raw))
            except json.JSONDecodeError as exc:
                logging.warning("Skipping malformed JSONL line %d: %s", line_no, exc)
    return records


def compute_hashes(data: bytes) -> tuple[str, str]:
    md5 = hashlib.md5(data).hexdigest()
    sha256 = hashlib.sha256(data).hexdigest()
    return md5, sha256


def init_database(db_path: Path, schema_path: Path) -> None:
    import sqlite3

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    schema_sql = schema_path.read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


def upsert_flight(
    db_path: Path,
    flight: dict[str, Any],
    valid: str,
    validation_reason: Optional[str],
    hash_value: Optional[str],
    downloaded_at: Optional[str],
) -> None:
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO flights (
                IDFlight, FlightDate, TakeoffLocation,
                Glider, BestTaskDistance, FlightDuration, IgcFilename,
                IgcFileHash, DownloadedAt, Valid, ValidationReason, LastUpdated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(IDFlight) DO UPDATE SET
                FlightDate=excluded.FlightDate,
                TakeoffLocation=excluded.TakeoffLocation,
                Glider=excluded.Glider,
                BestTaskDistance=excluded.BestTaskDistance,
                FlightDuration=excluded.FlightDuration,
                IgcFilename=excluded.IgcFilename,
                IgcFileHash=excluded.IgcFileHash,
                DownloadedAt=excluded.DownloadedAt,
                Valid=excluded.Valid,
                ValidationReason=excluded.ValidationReason,
                LastUpdated=excluded.LastUpdated;
            """,
            (
                flight.get("IDFlight"),
                flight.get("FlightDate"),
                flight.get("TakeoffLocation"),
                flight.get("Glider"),
                _to_float(flight.get("BestTaskDistance")),
                _to_int(flight.get("FlightDuration")),
                flight.get("IgcFilename"),
                hash_value,
                downloaded_at or flight.get("DownloadedAt"),
                valid,
                validation_reason,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def insert_flight_stats(
    db_path: Path,
    run_id: str,
    total: int,
    valid: int,
    invalid: int,
    missing: int,
    downloaded: int,
    started_at: str,
    finished_at: str,
) -> None:
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO flight_stats (
                run_id, total, valid, invalid, missing, downloaded,
                started_at, finished_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                total=excluded.total,
                valid=excluded.valid,
                invalid=excluded.invalid,
                missing=excluded.missing,
                downloaded=excluded.downloaded,
                started_at=excluded.started_at,
                finished_at=excluded.finished_at;
            """,
            (run_id, total, valid, invalid, missing, downloaded, started_at, finished_at),
        )
        conn.commit()
    finally:
        conn.close()


def validate_igc_file(igc_path: Path) -> tuple[str, Optional[str], Optional[str]]:
    if not igc_path.exists():
        return "missing", f"IGC file not found: {igc_path.name}", None
    try:
        data = igc_path.read_bytes()
    except OSError as exc:
        return "invalid", f"Could not read {igc_path.name}: {exc}", None
    if len(data) < MIN_IGC_SIZE:
        return "invalid", f"File too small ({len(data)} bytes, minimum {MIN_IGC_SIZE})", None
    try:
        text = data.decode("utf-8", errors="replace")
    except UnicodeDecodeError as exc:
        return "invalid", f"Not valid UTF-8 text: {exc}", None
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return "invalid", "IGC file contains no non-empty lines", None
    if not lines[0].startswith("A"):
        return "invalid", "Missing A-Record (file does not start with manufacturer record)", None
    b_indices = [i for i, line in enumerate(lines) if line.startswith("B")]
    if not b_indices:
        return "invalid", "No B-Records (position fixes) found", None
    g_indices = [i for i, line in enumerate(lines) if line.startswith("G")]
    if not g_indices:
        return "invalid", "Missing G-Record", None
    # The G-Record must appear after the last B-Record (security record closes the fixes).
    # Additional extension records (e.g. LX*) after the G-Record are allowed by many loggers.
    if g_indices[-1] < b_indices[-1]:
        return "invalid", "G-Record does not appear after the last B-Record", None
    md5, sha256 = compute_hashes(data)
    combined_hash = f"md5:{md5}|sha256:{sha256}"
    return "valid", None, combined_hash


def export_overview(export_dir: Path, run_id: str, stats: dict[str, Any]) -> Path:
    export_dir.mkdir(parents=True, exist_ok=True)
    overview = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": stats["total"],
        "downloaded": stats["downloaded"],
        "valid": stats["valid"],
        "invalid": stats["invalid"],
        "missing_igc": stats["missing"],
        "invalid_reasons": stats["invalid_reasons"],
        "note": (
            "Validation is structural only (A/B/G records, size, readability). "
            "G-Record cryptographic signatures are NOT verified."
        ),
    }
    export_path = export_dir / "flights_overview.json"
    with export_path.open("w", encoding="utf-8") as fh:
        json.dump(overview, fh, indent=2, ensure_ascii=False)
    return export_path


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="import-flights",
        description="Import flight metadata and IGC files into SQLite.",
    )
    parser.add_argument(
        "--flights-jsonl",
        type=Path,
        default=DEFAULT_FLIGHTS_JSONL,
        help="Path to flights.jsonl (default: data/processed/flights.jsonl).",
    )
    parser.add_argument(
        "--igc-dir",
        type=Path,
        default=DEFAULT_IGC_DIR,
        help="Directory with downloaded IGC files (default: data/igc).",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help="SQLite database path (default: data/igc-extractor.db).",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help="SQLite schema SQL path (default: data/schema.sql).",
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=DEFAULT_EXPORT_DIR,
        help="Directory for JSON overview export (default: data/export).",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=DEFAULT_LOG_DIR,
        help="Directory for log files (default: data/logs).",
    )
    parser.add_argument(
        "--run-id",
        help="Explicit run ID (default: UTC timestamp YYYYMMDD_HHMMSS).",
    )
    return parser.parse_args(args)


def main(args: Optional[list[str]] = None) -> int:
    parsed = _parse_args(args)
    run_id = parsed.run_id or generate_run_id()
    started_at = datetime.now(timezone.utc).isoformat()
    log_path = setup_logging(run_id, parsed.log_dir)
    logging.info("Starting import run %s", run_id)
    logging.info("Log file: %s", log_path)

    try:
        init_database(parsed.db, parsed.schema)
        logging.info("Database initialized: %s", parsed.db)

        flights = read_jsonl(parsed.flights_jsonl)
        total = len(flights)
        logging.info("Loaded %d flight records from %s", total, parsed.flights_jsonl)

        counts = {"valid": 0, "invalid": 0, "missing": 0, "downloaded": 0}
        invalid_reasons: dict[str, int] = {}
        missing_reasons: dict[str, int] = {}

        for flight in flights:
            igc_filename = flight.get("IgcFilename") or ""
            igc_path = parsed.igc_dir / igc_filename if igc_filename else parsed.igc_dir / "__no_filename__.igc"
            status, reason, file_hash = validate_igc_file(igc_path)
            if status != "missing":
                counts["downloaded"] += 1
            upsert_flight(
                db_path=parsed.db,
                flight=flight,
                valid=status,
                validation_reason=reason,
                hash_value=file_hash,
                downloaded_at=None,
            )
            counts[status] += 1
            if status == "invalid" and reason:
                invalid_reasons[reason] = invalid_reasons.get(reason, 0) + 1
            if status == "missing" and reason:
                missing_reasons[reason] = missing_reasons.get(reason, 0) + 1
            logging.info(
                "Flight %s -> %s%s",
                flight.get("IDFlight"),
                status,
                f" ({reason})" if reason else "",
            )

        finished_at = datetime.now(timezone.utc).isoformat()
        insert_flight_stats(
            db_path=parsed.db,
            run_id=run_id,
            total=total,
            valid=counts["valid"],
            invalid=counts["invalid"],
            missing=counts["missing"],
            downloaded=counts["downloaded"],
            started_at=started_at,
            finished_at=finished_at,
        )

        stats = {
            "total": total,
            "downloaded": counts["downloaded"],
            "valid": counts["valid"],
            "invalid": counts["invalid"],
            "missing": counts["missing"],
            "invalid_reasons": invalid_reasons,
            "missing_reasons": missing_reasons,
        }
        export_path = export_overview(parsed.export_dir, run_id, stats)
        logging.info("Exported overview to %s", export_path)
        logging.info(
            "Import finished: total=%d, downloaded=%d, valid=%d, invalid=%d, missing=%d",
            total,
            counts["downloaded"],
            counts["valid"],
            counts["invalid"],
            counts["missing"],
        )
        return 0

    except FileNotFoundError as exc:
        logging.error("%s", exc)
        return 2
    except Exception as exc:
        logging.exception("Import failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())

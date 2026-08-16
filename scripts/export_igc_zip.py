#!/usr/bin/env python3
"""
Export local IGC files into a structured ZIP archive.

This script reads flight metadata from ``data/processed/flights.jsonl`` and
optionally the validation status from ``data/igc-extractor.db``. It creates a
ZIP archive containing:

- ``README.txt``        : human readable cover sheet with pilot/sender name.
- ``export_meta.json``  : overview statistics and export metadata.
- ``flights.csv``       : detailed flight table.
- ``<IDFlight>_<FlightDate>_<TakeoffLocation>.igc`` : renamed IGC files.

The validation status included in the CSV is structural only (A/B/G records,
size, readability). Cryptographic G-Record signatures are NOT verified.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import os
import sqlite3
import sys
import tarfile
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


DEFAULT_FLIGHTS_JSONL = Path("data/processed/flights.jsonl")
DEFAULT_IGC_DIR = Path("data/igc")
DEFAULT_DB = Path("data/igc-extractor.db")
DEFAULT_OUTPUT_DIR = Path("data/export")
DEFAULT_LOG_DIR = Path("data/logs")
DEFAULT_PILOT_NAME = "Florian Knab"

META_FILENAME = "export_meta.json"
CSV_FILENAME = "flights.csv"
README_FILENAME = "README.txt"


class _FilenameSanitizer:
    """Re-usable sanitizer matching the conventions in download_igc.py."""

    _UNSAFE = set('\\/:*?"<>|')

    @classmethod
    def sanitize(cls, value: Optional[str]) -> str:
        if value is None:
            return ""
        return "".join(
            c if c not in cls._UNSAFE and c.isprintable() else "_" for c in str(value)
        )


@dataclass
class FlightRecord:
    """Internal representation of one flight for the export."""

    id_flight: int
    flight_date: Optional[str]
    takeoff_location: Optional[str]
    landing_location: Optional[str]
    glider: Optional[str]
    flight_duration: Optional[int]
    best_task_distance: Optional[float]
    igc_filename: Optional[str]
    igc_url: Optional[str]
    valid: Optional[str] = None
    source: dict[str, Any] = field(default_factory=dict)

    @property
    def archive_filename(self) -> str:
        """Name of the IGC file inside the archive."""
        parts = [str(self.id_flight)]
        if self.flight_date:
            parts.append(_FilenameSanitizer.sanitize(self.flight_date))
        if self.takeoff_location:
            parts.append(_FilenameSanitizer.sanitize(self.takeoff_location))
        return "_".join(parts) + ".igc"

    def csv_row(self) -> dict[str, Any]:
        return {
            "IDFlight": self.id_flight,
            "FlightDate": self.flight_date or "",
            "TakeoffLocation": self.takeoff_location or "",
            "LandingLocation": self.landing_location or "",
            "Glider": self.glider or "",
            "FlightDuration": self.flight_duration if self.flight_duration is not None else "",
            "BestTaskDistanceKm": self.best_task_distance if self.best_task_distance is not None else "",
            "IgcFilenameInArchive": self.archive_filename,
            "ValidStatus": self.valid or "unknown",
            "OriginalIgcFilename": self.igc_filename or "",
        }


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _setup_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, mode="w", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
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


def _read_valid_status(db_path: Path) -> dict[int, str]:
    """Return a mapping IDFlight -> Valid status from the SQLite database."""
    status: dict[int, str] = {}
    if not db_path.exists():
        logging.info("SQLite database not found at %s; validation status will be 'unknown'", db_path)
        return status
    try:
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.execute(
                "SELECT IDFlight, Valid FROM flights WHERE Valid IS NOT NULL"
            )
            for row in cursor:
                try:
                    flight_id = int(row[0])
                except (TypeError, ValueError):
                    continue
                status[flight_id] = row[1]
        finally:
            conn.close()
    except sqlite3.Error as exc:
        logging.warning("Could not read validation status from %s: %s", db_path, exc)
    return status


def _to_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_flight(record: dict[str, Any]) -> FlightRecord:
    flight_id = record.get("IDFlight")
    if flight_id is None:
        raise ValueError("Flight record has no 'IDFlight' field")
    return FlightRecord(
        id_flight=int(flight_id),
        flight_date=record.get("FlightDate") or None,
        takeoff_location=record.get("TakeoffLocation") or None,
        landing_location=record.get("LandingLocation") or None,
        glider=record.get("Glider") or None,
        flight_duration=_to_int(record.get("FlightDuration")),
        best_task_distance=_to_float(record.get("BestTaskDistance")),
        igc_filename=record.get("IgcFilename") or None,
        igc_url=record.get("IgcUrl") or None,
        source=record,
    )


def _build_flights(
    jsonl_path: Path,
    db_path: Path,
) -> tuple[list[FlightRecord], list[dict[str, Any]]]:
    if not jsonl_path.exists():
        raise FileNotFoundError(f"Flights JSONL not found: {jsonl_path}")

    valid_status = _read_valid_status(db_path)
    raw_records = _read_jsonl(jsonl_path)
    flights: list[FlightRecord] = []
    skipped: list[dict[str, Any]] = []
    for line_no, record in enumerate(raw_records, start=1):
        try:
            flight = _parse_flight(record)
        except ValueError as exc:
            logging.warning("Skipping invalid flight record on line %d: %s", line_no, exc)
            skipped.append({"line": line_no, "reason": str(exc), "record": record})
            continue
        flight.valid = valid_status.get(flight.id_flight)
        flights.append(flight)
    return flights, skipped


def _locate_igc_file(igc_dir: Path, flight: FlightRecord) -> Optional[Path]:
    """Find the local IGC file for a flight, trying several candidate names."""
    candidates: list[str] = []
    if flight.igc_filename:
        candidates.append(flight.igc_filename)
    candidates.append(flight.archive_filename)
    candidates.append(f"{flight.id_flight}.igc")

    for candidate in candidates:
        path = igc_dir / candidate
        if path.exists() and path.stat().st_size > 0:
            return path
    return None


def _compute_meta(flights: list[FlightRecord]) -> dict[str, Any]:
    total_flights = len(flights)
    dates = sorted(
        {f.flight_date for f in flights if f.flight_date},
    )
    durations = [f.flight_duration for f in flights if f.flight_duration is not None]
    distances = [f.best_task_distance for f in flights if f.best_task_distance is not None]
    takeoffs = {f.takeoff_location for f in flights if f.takeoff_location}

    best_flight: Optional[FlightRecord] = None
    if flights:
        best_flight = max(
            (f for f in flights if f.best_task_distance is not None),
            key=lambda f: f.best_task_distance or 0.0,
            default=None,
        )

    earliest = dates[0] if dates else None
    latest = dates[-1] if dates else None
    period_label = ""
    if earliest and latest:
        if earliest == latest:
            period_label = earliest
        else:
            period_label = f"{earliest} bis {latest}"
    elif earliest:
        period_label = earliest
    elif latest:
        period_label = latest

    return {
        "total_flights": total_flights,
        "total_igc_files": total_flights,
        "total_flight_duration_minutes": sum(durations) if durations else 0,
        "sum_xc_distance_overall_flights": round(sum(distances), 3) if distances else 0.0,
        "best_single_flight_distance_km": round(best_flight.best_task_distance, 3) if best_flight and best_flight.best_task_distance is not None else None,
        "best_single_flight": {
            "IDFlight": best_flight.id_flight,
            "FlightDate": best_flight.flight_date,
            "TakeoffLocation": best_flight.takeoff_location,
            "Glider": best_flight.glider,
        } if best_flight else None,
        "period": {
            "earliest_flight_date": earliest,
            "latest_flight_date": latest,
            "period_label": period_label,
        },
        "unique_takeoff_locations": len(takeoffs),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "validation_note": (
            "Validation is structural only (A/B/G records, file size, readability). "
            "Cryptographic G-Record signatures are NOT verified."
        ),
    }


def _build_readme(meta: dict[str, Any], pilot_name: str) -> bytes:
    """Return a short, plain-text README for the archive."""
    period_label = meta.get("period", {}).get("period_label") or "unbekannter Zeitraum"
    total_flights = meta.get("total_flights", 0)
    duration = meta.get("total_flight_duration_minutes", 0)
    sum_distances = meta.get("sum_xc_distance_overall_flights", 0.0)
    best_single = meta.get("best_single_flight_distance_km")
    best_flight = meta.get("best_single_flight")
    takeoffs = meta.get("unique_takeoff_locations", 0)
    generated = meta.get("generated_at", "unbekannt")

    lines = [
        "IGC-Flugarchiv - Kurzbeschreibung",
        "==================================",
        "",
        f"Pilot / Absender: {pilot_name}",
        f"Dieses Archiv enthaelt {total_flights} IGC-Datei(en) von Paragliding- bzw.",
        "Gleitschirmfluegen.",
        "",
        f"Zeitraum:          {period_label}",
        f"Startorte:         {takeoffs} unterschiedliche(r)",
        f"Gesamtflugzeit:    ca. {duration} Minuten",
        f"Summe XC-Distanz:  ca. {sum_distances} km",
    ]
    if best_single is not None and best_flight:
        lines.append(
            f"Bester einzelner Flug: {best_single} km "
            f"(Flug {best_flight.get('IDFlight')} am {best_flight.get('FlightDate')}, "
            f"{best_flight.get('TakeoffLocation')})"
        )
    lines.extend([
        f"Erstellt am:       {generated}",
        "",
        "Hinweis zur strukturellen Validierung",
        "-------------------------------------",
        "",
        "Der Validierungsstatus ist rein strukturell geprueft (A-/B-/G-Records,",
        "Lesbarkeit). Eine kryptographische G-Record-Pruefung findet NICHT statt.",
        "",
        f"Bei Fragen zum Archiv wende dich bitte an {pilot_name}.",
        "",
    ])
    return "\n".join(lines).encode("utf-8")


def _write_meta_csv_and_readme(
    archive: zipfile.ZipFile | tarfile.TarFile,
    meta: dict[str, Any],
    flights: list[FlightRecord],
    pilot_name: str,
) -> None:
    readme_bytes = _build_readme(meta, pilot_name)
    meta_bytes = json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8")

    csv_buffer = io.StringIO()
    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=[
            "IDFlight",
            "FlightDate",
            "TakeoffLocation",
            "LandingLocation",
            "Glider",
            "FlightDuration",
            "BestTaskDistanceKm",
            "IgcFilenameInArchive",
            "ValidStatus",
            "OriginalIgcFilename",
        ],
    )
    writer.writeheader()
    for flight in flights:
        writer.writerow(flight.csv_row())
    csv_bytes = csv_buffer.getvalue().encode("utf-8")

    if isinstance(archive, zipfile.ZipFile):
        archive.writestr(README_FILENAME, readme_bytes)
        archive.writestr(META_FILENAME, meta_bytes)
        archive.writestr(CSV_FILENAME, csv_bytes)
        return

    # tar.gz path
    now = datetime.now(timezone.utc).timestamp()
    readme_info = tarfile.TarInfo(name=README_FILENAME)
    readme_info.size = len(readme_bytes)
    readme_info.mtime = now
    archive.addfile(readme_info, io.BytesIO(readme_bytes))

    meta_info = tarfile.TarInfo(name=META_FILENAME)
    meta_info.size = len(meta_bytes)
    meta_info.mtime = now
    archive.addfile(meta_info, io.BytesIO(meta_bytes))

    csv_info = tarfile.TarInfo(name=CSV_FILENAME)
    csv_info.size = len(csv_bytes)
    csv_info.mtime = now
    archive.addfile(csv_info, io.BytesIO(csv_bytes))


def _write_zip_archive(
    output_path: Path,
    flights: list[FlightRecord],
    igc_dir: Path,
    logger: logging.Logger,
    pilot_name: str,
) -> tuple[list[FlightRecord], list[FlightRecord]]:
    """Write the ZIP archive. Returns (exported, missing)."""
    meta = _compute_meta(flights)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    exported: list[FlightRecord] = []
    missing: list[FlightRecord] = []

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        _write_meta_csv_and_readme(zf, meta, flights, pilot_name)
        for flight in flights:
            igc_path = _locate_igc_file(igc_dir, flight)
            if igc_path is None:
                missing.append(flight)
                logger.warning(
                    "No local IGC file found for flight %s (tried %s)",
                    flight.id_flight,
                    flight.igc_filename or flight.archive_filename,
                )
                continue
            arcname = flight.archive_filename
            zf.write(igc_path, arcname)
            exported.append(flight)
            logger.info(
                "Added %s -> %s (%d bytes)",
                igc_path.name,
                arcname,
                igc_path.stat().st_size,
            )

    return exported, missing


def _write_tar_gz_archive(
    output_path: Path,
    flights: list[FlightRecord],
    igc_dir: Path,
    logger: logging.Logger,
    pilot_name: str,
) -> tuple[list[FlightRecord], list[FlightRecord]]:
    """Write a tar.gz archive. Returns (exported, missing)."""
    meta = _compute_meta(flights)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    exported: list[FlightRecord] = []
    missing: list[FlightRecord] = []

    with tarfile.open(output_path, "w:gz") as tf:
        _write_meta_csv_and_readme(tf, meta, flights, pilot_name)
        for flight in flights:
            igc_path = _locate_igc_file(igc_dir, flight)
            if igc_path is None:
                missing.append(flight)
                logger.warning(
                    "No local IGC file found for flight %s (tried %s)",
                    flight.id_flight,
                    flight.igc_filename or flight.archive_filename,
                )
                continue
            tf.add(igc_path, arcname=flight.archive_filename)
            exported.append(flight)
            logger.info(
                "Added %s -> %s (%d bytes)",
                igc_path.name,
                flight.archive_filename,
                igc_path.stat().st_size,
            )

    return exported, missing


def _parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="export-igc-zip",
        description="Export local IGC files into a structured archive.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for the generated archive (default: data/export).",
    )
    parser.add_argument(
        "--igc-dir",
        type=Path,
        default=DEFAULT_IGC_DIR,
        help="Directory containing the local IGC files (default: data/igc).",
    )
    parser.add_argument(
        "--flights-jsonl",
        type=Path,
        default=DEFAULT_FLIGHTS_JSONL,
        help="Path to flights.jsonl (default: data/processed/flights.jsonl).",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help="SQLite database path for validation status (default: data/igc-extractor.db).",
    )
    parser.add_argument(
        "--output-name",
        type=str,
        default=None,
        help="Optional archive file name. Default: igc_export_<run_id>.zip",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=("zip", "tar.gz"),
        default="zip",
        help="Archive format (default: zip; tar.gz is also supported).",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=DEFAULT_LOG_DIR,
        help="Directory for log and summary files (default: data/logs).",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Explicit run ID (default: UTC timestamp YYYYMMDD_HHMMSS_uuid).",
    )
    parser.add_argument(
        "--pilot-name",
        "--sender",
        type=str,
        default=DEFAULT_PILOT_NAME,
        dest="pilot_name",
        help=(
            "Name of the pilot or sender to write into README.txt "
            f"(default: {DEFAULT_PILOT_NAME})."
        ),
    )
    return parser.parse_args(args)


def _resolve_paths(parsed: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path]:
    project_root = _project_root()
    output_dir = project_root / parsed.output_dir
    igc_dir = project_root / parsed.igc_dir
    flights_jsonl = project_root / parsed.flights_jsonl
    db = project_root / parsed.db
    log_dir = project_root / parsed.log_dir
    return output_dir, igc_dir, flights_jsonl, db, log_dir


def main(args: Optional[list[str]] = None) -> int:
    parsed = _parse_args(args)

    output_dir, igc_dir, flights_jsonl, db, log_dir = _resolve_paths(parsed)

    run_id = parsed.run_id or (
        datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    )
    log_path = log_dir / f"export_igc_zip_{run_id}.log"
    summary_path = log_dir / f"export_igc_zip_summary_{run_id}.json"

    started_at = datetime.now(timezone.utc).isoformat()

    _setup_logging(log_path)
    logger = logging.getLogger(__name__)

    logger.info("Starting export_igc_zip run %s", run_id)
    logger.info("flights_jsonl: %s", flights_jsonl)
    logger.info("igc_dir:       %s", igc_dir)
    logger.info("db:            %s", db)
    logger.info("output_dir:    %s", output_dir)
    logger.info("format:        %s", parsed.format)
    logger.info("pilot_name:    %s", parsed.pilot_name)

    try:
        flights, skipped = _build_flights(flights_jsonl, db)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2

    logger.info("Loaded %d flight record(s) from JSONL", len(flights))
    if skipped:
        logger.warning("Skipped %d malformed record(s)", len(skipped))

    extension = ".zip" if parsed.format == "zip" else ".tar.gz"
    if parsed.output_name:
        archive_name = parsed.output_name
        if not archive_name.endswith(extension):
            archive_name += extension
    else:
        archive_name = f"igc_export_{run_id}{extension}"
    output_path = output_dir / archive_name

    if parsed.format == "zip":
        exported, missing = _write_zip_archive(output_path, flights, igc_dir, logger, parsed.pilot_name)
    else:
        exported, missing = _write_tar_gz_archive(output_path, flights, igc_dir, logger, parsed.pilot_name)

    finished_at = datetime.now(timezone.utc).isoformat()
    summary = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "total": len(flights),
        "exported": len(exported),
        "skipped": len(skipped),
        "missing": len(missing),
        "output_path": str(output_path),
        "format": parsed.format,
        "missing_flights": [f.id_flight for f in missing],
        "skipped_records": [
            {"line": s["line"], "reason": s["reason"]} for s in skipped
        ],
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    logger.info("Export written to %s", output_path)
    logger.info(
        "Summary: total=%d, exported=%d, skipped=%d, missing=%d",
        summary["total"],
        summary["exported"],
        summary["skipped"],
        summary["missing"],
    )
    logger.info("Summary file: %s", summary_path)

    if missing:
        logger.warning("Archive is incomplete: %d IGC file(s) missing", len(missing))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

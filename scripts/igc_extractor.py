#!/usr/bin/env python3
"""
igc-extractor CLI tool.

Downloads paragliding flight tracks (IGC files) from dhv-xc.de.
The tool is intentionally lightweight: plain Python + requests/BeautifulSoup,
local SQLite/JSONL storage, idempotent execution with resume support,
and credentials sourced from environment variables / .env.

This script orchestrates the full pipeline:

    1. list_flights.py  - fetch / update ``data/processed/flights.jsonl``.
    2. download_igc.py  - download IGC files for the requested subset.
    3. import_flights.py - import metadata + IGC files into SQLite and validate.

See docs/decisions/ADR-001-architecture-techstack.md for architectural
principles and /home/florian/github.com/Vollol1/gag-atlas/docs/decisions/ADR-007-secrets-management.md
for secrets handling.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _load_dotenv_if_available() -> None:
    """Load .env into os.environ when python-dotenv is installed."""
    try:
        from dotenv import load_dotenv  # type: ignore
        dotenv_path = Path(__file__).resolve().parent.parent / ".env"
        load_dotenv(dotenv_path, override=False)
    except ImportError:
        pass


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="igc-extractor",
        description="Download IGC flight tracks from dhv-xc.de.",
    )
    parser.add_argument(
        "--flights",
        type=int,
        default=200,
        help="Number of flights to download (default: 200).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/igc"),
        help="Directory for downloaded IGC files (default: data/igc).",
    )
    parser.add_argument(
        "--state-db",
        type=Path,
        default=Path("data/igc_extractor.db"),
        help="SQLite state database for resume/idempotence (default: data/igc_extractor.db).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip already downloaded flights and continue where the previous run left off.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List flights that would be downloaded without writing files.",
    )
    parser.add_argument(
        "--username",
        help="DHV-XC username (overrides DHV_XC_USERNAME from environment).",
    )
    parser.add_argument(
        "--password",
        help="DHV-XC password (overrides DHV_XC_PASSWORD from environment).",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DHV_XC_BASE_URL", "https://www.dhv-xc.de"),
        help="DHV-XC base URL (default: https://www.dhv-xc.de).",
    )
    parser.add_argument(
        "--pilot-id",
        type=int,
        default=int(os.environ["DHV_XC_PILOT_ID"]) if os.environ.get("DHV_XC_PILOT_ID") else None,
        help="Optional pilot ID (overrides DHV_XC_PILOT_ID).",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=1.0,
        help="Seconds to wait between consecutive IGC downloads (default: 1.0).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum download attempts per IGC file (default: 3).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Download flights in batches of N, re-authenticating between batches (default: 50).",
    )
    parser.add_argument(
        "--batch-pause",
        type=int,
        default=10,
        help="Seconds to pause between download batches (default: 10).",
    )
    return parser.parse_args(args)


def _validate_credentials(parsed: argparse.Namespace) -> tuple[str, str]:
    """Return (username, password) from CLI or environment, failing hard if absent."""
    username = parsed.username or os.environ.get("DHV_XC_USERNAME")
    password = parsed.password or os.environ.get("DHV_XC_PASSWORD")
    if not username or not password:
        raise RuntimeError(
            "DHV-XC credentials are required. Provide them via .env "
            "(DHV_XC_USERNAME / DHV_XC_PASSWORD), environment variables, "
            "or --username / --password. Never commit credentials to Git."
        )
    return username, password


def _sanitize_filename(value: str) -> str:
    """Mirror the safe-filename logic used by download_igc.py."""
    unsafe = set('\\\\/:*?"<>|')
    return "".join(c if c not in unsafe and c.isprintable() else "_" for c in value)


def _igc_filename(record: dict[str, Any]) -> str:
    """Build the IGC filename exactly as download_igc.py does."""
    flight_id = record["IDFlight"]
    parts = [str(flight_id)]
    date = record.get("FlightDate")
    if date:
        parts.append(_sanitize_filename(str(date)))
    takeoff = record.get("TakeoffLocation")
    if takeoff:
        parts.append(_sanitize_filename(str(takeoff)))
    if len(parts) > 1:
        return "_".join(parts) + ".igc"
    return f"{flight_id}.igc"


def _setup_logging(run_id: str, logs_dir: Path) -> Path:
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"igc_extractor_run_{run_id}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, mode="w", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return log_path


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logging.warning("Skipping malformed JSONL line: %s", exc)
    return records


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _prepare_download_subset(
    all_flights_path: Path,
    limit: int,
    subset_path: Path,
) -> int:
    """
    Read the full flight list, keep the ``limit`` newest flights, enrich each
    record with ``IgcFilename`` (so import_flights.py can locate the file),
    and write a subset JSONL for the download/import steps.
    """
    all_records = _read_jsonl(all_flights_path)
    if not all_records:
        return 0
    subset = all_records[:limit]
    for record in subset:
        record["IgcFilename"] = _igc_filename(record)
    _write_jsonl(subset_path, subset)
    return len(subset)


def _run_subprocess(
    script_name: str,
    args: list[str],
    project_root: Path,
    logger: logging.Logger,
) -> int:
    """Run one of the pipeline scripts via the same Python interpreter."""
    script_path = project_root / "scripts" / script_name
    cmd = [sys.executable, str(script_path)] + args
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(project_root), check=False)
    logger.info("%s finished with exit code %d", script_name, result.returncode)
    return result.returncode


def _run_list_flights(
    parsed: argparse.Namespace,
    project_root: Path,
    logger: logging.Logger,
) -> int:
    """Update data/processed/flights.jsonl with all own flights."""
    flights_jsonl = project_root / "data" / "processed" / "flights.jsonl"
    args = [
        "--base-url", parsed.base_url,
        "--username", parsed.username or "",
        "--password", parsed.password or "",
        "--output", str(flights_jsonl),
    ]
    return _run_subprocess("list_flights.py", args, project_root, logger)


def _run_download_igc(
    parsed: argparse.Namespace,
    flights_jsonl: Path,
    project_root: Path,
    logger: logging.Logger,
) -> int:
    """Download IGC files for the subset of flights in batches."""
    output_dir = project_root / parsed.output_dir
    all_records = _read_jsonl(flights_jsonl)
    total = len(all_records)
    if total == 0:
        return 0

    batch_size = parsed.batch_size
    max_rc = 0
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        logger.info(
            "Downloading batch %d-%d of %d (batch_size=%d)",
            start + 1,
            end,
            total,
            batch_size,
        )
        args = [
            "--flights-jsonl", str(flights_jsonl),
            "--output-dir", str(output_dir),
            "--logs-dir", str(project_root / "data" / "logs"),
            "--base-url", parsed.base_url,
            "--username", parsed.username or "",
            "--password", parsed.password or "",
            "--rate-limit", str(parsed.rate_limit),
            "--max-retries", str(parsed.max_retries),
            "--offset", str(start),
            "--limit", str(batch_size),
        ]
        rc = _run_subprocess("download_igc.py", args, project_root, logger)
        if rc != 0:
            logger.error("Download batch %d-%d finished with exit code %d", start + 1, end, rc)
            max_rc = rc
        if end < total and parsed.batch_pause > 0:
            logger.info("Pausing %d s between download batches", parsed.batch_pause)
            time.sleep(parsed.batch_pause)
    if parsed.resume:
        logger.info("Resume requested: existing IGC files within each batch will be skipped")
    return max_rc


def _run_import_flights(
    parsed: argparse.Namespace,
    flights_jsonl: Path,
    project_root: Path,
    logger: logging.Logger,
    run_id: str,
) -> int:
    """Import metadata and IGC files into SQLite."""
    args = [
        "--flights-jsonl", str(flights_jsonl),
        "--igc-dir", str(project_root / parsed.output_dir),
        "--db", str(project_root / parsed.state_db),
        "--schema", str(project_root / "data" / "schema.sql"),
        "--export-dir", str(project_root / "data" / "export"),
        "--log-dir", str(project_root / "data" / "logs"),
        "--run-id", run_id,
    ]
    return _run_subprocess("import_flights.py", args, project_root, logger)


def _print_dry_run_preview(
    all_records: list[dict[str, Any]],
    limit: int,
    output_dir: Path,
) -> None:
    """Show what a real run would do without touching downloads/imports."""
    total = len(all_records)
    subset = all_records[:limit]
    print(f"\nDry-run preview ({len(subset)} of {total} flights would be processed):\n")
    for idx, record in enumerate(subset, start=1):
        print(
            f"  {idx}. Flight {record.get('IDFlight')} "
            f"- {record.get('FlightDate')} - {record.get('TakeoffLocation')} "
            f"- {_igc_filename(record)}"
        )
    print(
        f"\nWould download up to {len(subset)} IGC file(s) to {output_dir} "
        f"and import them into the SQLite database."
    )
    print("No files were downloaded or written to the database in this run.")


def main(args: Optional[list[str]] = None) -> int:
    _load_dotenv_if_available()
    parsed = _parse_args(args)

    try:
        username, password = _validate_credentials(parsed)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    project_root = _project_root()
    output_dir = project_root / parsed.output_dir
    state_db = project_root / parsed.state_db

    output_dir.mkdir(parents=True, exist_ok=True)
    state_db.parent.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    logs_dir = project_root / "data" / "logs"
    log_path = _setup_logging(run_id, logs_dir)
    logger = logging.getLogger(__name__)

    logger.info("Starting igc-extractor run %s", run_id)
    logger.info("Log file: %s", log_path)
    logger.info("base_url:   %s", parsed.base_url)
    logger.info("username:   %s", username)
    logger.info("pilot_id:   %s", parsed.pilot_id)
    logger.info("flights:    %d", parsed.flights)
    logger.info("output_dir: %s", output_dir)
    logger.info("state_db:   %s", state_db)
    logger.info("resume:     %s", parsed.resume)
    logger.info("dry_run:    %s", parsed.dry_run)
    logger.info("rate_limit: %.1f s", parsed.rate_limit)
    logger.info("max_retries: %d", parsed.max_retries)

    print(f"igc-extractor configured:")
    print(f"  base_url:   {parsed.base_url}")
    print(f"  username:   {username}")
    print(f"  pilot_id:   {parsed.pilot_id}")
    print(f"  flights:    {parsed.flights}")
    print(f"  output_dir: {output_dir}")
    print(f"  state_db:   {state_db}")
    print(f"  resume:     {parsed.resume}")
    print(f"  dry_run:    {parsed.dry_run}")
    print(f"  rate_limit: {parsed.rate_limit} s")
    print(f"  max_retries: {parsed.max_retries}")

    list_rc = _run_list_flights(parsed, project_root, logger)
    if list_rc != 0:
        logger.error("Flight list step failed with exit code %d", list_rc)
        return list_rc

    all_flights_path = project_root / "data" / "processed" / "flights.jsonl"
    all_records = _read_jsonl(all_flights_path)
    logger.info("Flight list contains %d record(s)", len(all_records))

    if parsed.dry_run:
        _print_dry_run_preview(all_records, parsed.flights, output_dir)
        logger.info("Dry run finished, no downloads or imports performed")
        return 0

    subset_path = project_root / "data" / "processed" / "flights_to_download.jsonl"
    subset_count = _prepare_download_subset(all_flights_path, parsed.flights, subset_path)
    logger.info(
        "Prepared download subset with %d of %d flight(s) at %s",
        subset_count,
        len(all_records),
        subset_path,
    )

    if subset_count == 0:
        print("No flights found to download.")
        return 0

    download_rc = _run_download_igc(parsed, subset_path, project_root, logger)
    if download_rc != 0:
        logger.error("Download step finished with exit code %d", download_rc)

    import_rc = _run_import_flights(parsed, subset_path, project_root, logger, run_id)
    if import_rc != 0:
        logger.error("Import step finished with exit code %d", import_rc)

    final_rc = download_rc if download_rc != 0 else import_rc
    if final_rc == 0:
        logger.info("igc-extractor run %s completed successfully", run_id)
    else:
        logger.warning("igc-extractor run %s finished with exit code %d", run_id, final_rc)
    return final_rc


if __name__ == "__main__":
    sys.exit(main())

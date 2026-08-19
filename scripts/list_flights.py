#!/usr/bin/env python3
"""
scripts/list_flights.py

List all own flights from dhv-xc.de (filters ``mine=1`` and ``incpriv=1``),
extract metadata for each flight and write them idempotently to
``data/processed/flights.jsonl``.

Credentials are read exclusively from environment variables or a local ``.env``
file (``DHV_XC_USERNAME`` / ``DHV_XC_PASSWORD``). They are never written to
the source code or log files.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import requests

try:
    from tqdm import tqdm  # type: ignore
except ImportError:  # pragma: no cover
    def tqdm(iterable, *args, **kwargs):  # type: ignore[no-redef]
        return iterable

from common import project_root, read_jsonl, write_jsonl
from dhv_xc_client import (
    DEFAULT_BASE_URL,
    DhvXcClient,
    IGC_DOWNLOAD_PATH_TEMPLATE,
    PAGE_SIZE,
    load_dotenv_if_available,
    now_iso,
)


TARGET_MIN_FLIGHTS = 200

_DISCLAIMER = (
    "Hinweis: Dieses Tool greift mit deinen Credentials auf eine Flugdatenplattform zu. "
    "Du nutzt es auf eigene Gefahr. Ein Account-Bann oder andere Sanktionen seitens der "
    "Plattform sind möglich. Stelle sicher, dass du die geltenden Nutzungsbedingungen einhältst."
)


def _print_disclaimer() -> None:
    """Print a short, non-blocking disclaimer at startup."""
    print(_DISCLAIMER, file=sys.stderr)


@dataclass(frozen=True, slots=True)
class FlightRecord:
    """Immutable flight metadata record written to JSONL."""

    IDFlight: int
    FlightDate: Optional[str]
    TakeoffLocation: Optional[str]
    Glider: Optional[str]
    BestTaskDistance: Optional[float]
    FlightDuration: Optional[int]
    IgcUrl: str
    ExtractedAt: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_dotenv() -> None:
    load_dotenv_if_available()


def _flight_duration_minutes(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(round(float(value) / 60))
    except (TypeError, ValueError):
        return None


def _best_task_distance_km(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return round(float(value) / 1000, 3)
    except (TypeError, ValueError):
        return None


def _extract_flight(row: dict[str, Any], base_url: str) -> FlightRecord:
    flight_id = int(row["IDFlight"])
    takeoff: Optional[str] = None
    glider: Optional[str] = None

    for key in ("TakeoffLocation", "TakeoffName", "StartLocation", "Startort"):
        if row.get(key):
            takeoff = str(row[key]).strip() or None
            if takeoff:
                break

    if not takeoff:
        fk = row.get("FKTakeoffWaypoint")
        if fk:
            takeoff = f"FKTakeoffWaypoint:{fk}"

    for key in ("Glider", "GliderName", "Gleitschirm"):
        if row.get(key):
            glider = str(row[key]).strip() or None
            if glider:
                break

    if not glider:
        fk = row.get("FKGlider")
        if fk:
            glider = f"FKGlider:{fk}"

    return FlightRecord(
        IDFlight=flight_id,
        FlightDate=row.get("FlightDate") or None,
        TakeoffLocation=takeoff,
        Glider=glider,
        BestTaskDistance=_best_task_distance_km(row.get("BestTaskDistance")),
        FlightDuration=_flight_duration_minutes(row.get("FlightDuration")),
        IgcUrl=urljoin(base_url, IGC_DOWNLOAD_PATH_TEMPLATE.format(id=flight_id)),
        ExtractedAt=now_iso(),
    )


def _merge_idempotent(
    existing: list[dict[str, Any]],
    fetched: list[FlightRecord],
) -> list[FlightRecord]:
    merged: dict[int, dict[str, Any]] = {}
    for row in existing:
        try:
            fid = int(row["IDFlight"])
        except (KeyError, TypeError, ValueError):
            continue
        merged[fid] = dict(row)

    for rec in fetched:
        fid = rec.IDFlight
        if fid in merged:
            merged[fid].update(rec.to_dict())
        else:
            merged[fid] = rec.to_dict()

    def sort_key(item: dict[str, Any]) -> tuple[str, int]:
        date = item.get("FlightDate") or "0000-00-00"
        return (date, -int(item["IDFlight"]))

    return [FlightRecord(**row) for row in sorted(merged.values(), key=sort_key, reverse=True)]


def _parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="list_flights.py",
        description="List own flights from a supported flight-data platform (default: dhv-xc.de) and write them to JSONL.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DHV_XC_BASE_URL", DEFAULT_BASE_URL),
        help="Base URL of the flight-data platform (default: https://www.dhv-xc.de).",
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("DHV_XC_USERNAME"),
        help="DHV-XC username (overrides DHV_XC_USERNAME).",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("DHV_XC_PASSWORD"),
        help="DHV-XC password (overrides DHV_XC_PASSWORD).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/flights.jsonl"),
        help="Output JSONL path (default: data/processed/flights.jsonl).",
    )
    parser.add_argument(
        "--min-flights",
        type=int,
        default=TARGET_MIN_FLIGHTS,
        help=f"Minimum number of flights expected (default: {TARGET_MIN_FLIGHTS}).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=PAGE_SIZE,
        help=f"Page size for API pagination (default: {PAGE_SIZE}).",
    )
    return parser.parse_args(args)


def main(args: Optional[list[str]] = None) -> int:
    _load_dotenv()
    parsed = _parse_args(args)

    _print_disclaimer()

    username = parsed.username or os.environ.get("DHV_XC_USERNAME")
    password = parsed.password or os.environ.get("DHV_XC_PASSWORD")
    if not username or not password:
        print(
            "Error: DHV-XC credentials are required. Provide them via .env "
            "(DHV_XC_USERNAME / DHV_XC_PASSWORD), environment variables, "
            "or --username / --password.",
            file=sys.stderr,
        )
        return 1

    run_id = uuid.uuid4().hex[:12]
    root = project_root()
    output_path = root / parsed.output
    log_path = root / "data" / "logs" / f"list_flights_{run_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.info("Run ID: %s", run_id)
    logging.info("Output path: %s", output_path)
    logging.info("Base URL: %s", parsed.base_url)

    client = DhvXcClient(parsed.base_url, username, password)
    try:
        client.login()
        logging.info("Authenticated successfully as %s", username)
    except RuntimeError as exc:
        logging.error("Authentication failed: %s", exc)
        return 1

    fetched_records: list[FlightRecord] = []
    start = 0
    total_known: Optional[int] = None

    pbar = tqdm(desc="Flights", unit=" flights")

    while True:
        try:
            page = client.get_flight_page(start=start, limit=parsed.page_size)
        except RuntimeError as exc:
            logging.error("Failed to fetch flight page starting at %s: %s", start, exc)
            return 1

        if not page.get("success"):
            meta = page.get("meta", {})
            msg = page.get("message") or meta.get("message") or "Unknown API error"
            logging.error("Flight API error: %s", msg)
            return 1

        rows = page.get("data", [])
        if not rows:
            break

        if total_known is None:
            meta = page.get("meta", {})
            total_known = page.get("total") or meta.get("total") or len(rows)
            logging.info("Flight API reports up to %s total flights", total_known)
            pbar.total = total_known

        for row in rows:
            try:
                fetched_records.append(_extract_flight(row, parsed.base_url))
            except Exception as exc:
                logging.warning("Skipping row due to extraction error: %s", exc)
        pbar.update(len(rows))

        if len(rows) < parsed.page_size:
            break
        start += parsed.page_size

    pbar.close()
    logging.info("Fetched %s flight record(s)", len(fetched_records))

    if len(fetched_records) < parsed.min_flights:
        logging.warning(
            "Expected at least %s flights but only found %s. "
            "Check filters or verify that the account has enough private/own flights.",
            parsed.min_flights,
            len(fetched_records),
        )

    existing = read_jsonl(output_path)
    merged = _merge_idempotent(existing, fetched_records)
    write_jsonl(output_path, merged)

    logging.info("Wrote %s flight record(s) to %s", len(merged), output_path)
    print(f"Login successful, {len(fetched_records)} flight(s) fetched, "
          f"{len(merged)} record(s) in {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

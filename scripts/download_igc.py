#!/usr/bin/env python3
"""Download IGC files for flights listed in data/processed/flights.jsonl."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
        dotenv_path = Path(__file__).resolve().parent.parent / ".env"
        load_dotenv(dotenv_path, override=False)
    except ImportError:
        pass


def _sanitize_filename(value: str) -> str:
    unsafe = set('\\/:*?"<>|')
    return "".join(c if c not in unsafe and c.isprintable() else "_" for c in value)


def _setup_logging(log_file: Path) -> logging.Logger:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger(__name__)


@dataclass
class Flight:
    id: int
    date: Optional[str]
    takeoff: Optional[str]
    igc_url: Optional[str]
    raw: dict[str, Any]

    @property
    def igc_filename(self) -> str:
        parts = [str(self.id)]
        if self.date:
            parts.append(_sanitize_filename(self.date))
        if self.takeoff:
            parts.append(_sanitize_filename(self.takeoff))
        if len(parts) > 1:
            return "_".join(parts) + ".igc"
        return f"{self.id}.igc"

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "Flight":
        flight_id = record.get("id") or record.get("flight_id")
        if flight_id is None:
            raise ValueError("Flight record has no 'id' or 'flight_id' field")
        flight_id = int(flight_id)
        date = record.get("date") or record.get("flight_date")
        takeoff = record.get("takeoff") or record.get("takeoff_site") or record.get("site")
        igc_url = record.get("igc_url") or record.get("track_url") or record.get("url")
        return cls(id=flight_id, date=date, takeoff=takeoff, igc_url=igc_url, raw=record)


@dataclass
class Summary:
    run_id: str
    started_at: str
    finished_at: Optional[str] = None
    total: int = 0
    downloaded: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(
                {
                    "run_id": self.run_id,
                    "started_at": self.started_at,
                    "finished_at": self.finished_at,
                    "total": self.total,
                    "downloaded": self.downloaded,
                    "skipped": self.skipped,
                    "failed": self.failed,
                    "errors": self.errors,
                },
                fh,
                ensure_ascii=False,
                indent=2,
            )


def _parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="download_igc",
        description="Download IGC files for flights in data/processed/flights.jsonl.",
    )
    parser.add_argument(
        "--flights-jsonl",
        type=Path,
        default=Path("data/processed/flights.jsonl"),
        help="Path to the flights JSONL file (default: data/processed/flights.jsonl).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/igc"),
        help="Directory for downloaded IGC files (default: data/igc).",
    )
    parser.add_argument(
        "--logs-dir",
        type=Path,
        default=Path("data/logs"),
        help="Directory for logs and summaries (default: data/logs).",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DHV_XC_BASE_URL", "https://www.dhv-xc.de"),
        help="DHV-XC base URL (default: https://www.dhv-xc.de).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download IGC files even if they already exist.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of download attempts per flight (default: 3).",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=1.0,
        help="Seconds to wait between consecutive requests (default: 1.0).",
    )
    parser.add_argument(
        "--username",
        help="DHV-XC username (overrides DHV_XC_USERNAME from environment).",
    )
    parser.add_argument(
        "--password",
        help="DHV-XC password (overrides DHV_XC_PASSWORD from environment).",
    )
    return parser.parse_args(args)


def _resolve_credentials(parsed: argparse.Namespace) -> tuple[str, str]:
    username = parsed.username or os.environ.get("DHV_XC_USERNAME")
    password = parsed.password or os.environ.get("DHV_XC_PASSWORD")
    if not username or not password:
        raise RuntimeError(
            "DHV-XC credentials are required. Provide them via .env "
            "(DHV_XC_USERNAME / DHV_XC_PASSWORD), environment variables, "
            "or --username / --password. Never commit credentials to Git."
        )
    return username, password


def _read_flights(path: Path) -> list[Flight]:
    flights: list[Flight] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_no}: {exc}") from exc
            try:
                flights.append(Flight.from_record(record))
            except ValueError as exc:
                raise ValueError(f"Invalid flight record on line {line_no}: {exc}") from exc
    return flights


def _needs_download(output_path: Path, force: bool) -> bool:
    if force:
        return True
    return not (output_path.exists() and output_path.stat().st_size > 0)


def _download_with_retry(
    session,
    url: str,
    output_path: Path,
    flight_id: int,
    max_retries: int,
    logger: logging.Logger,
) -> bool:
    last_exception: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            if output_path.stat().st_size == 0:
                raise RuntimeError("Downloaded file is empty")
            logger.info(
                "Downloaded flight %s (%d bytes) on attempt %d/%d",
                flight_id,
                output_path.stat().st_size,
                attempt,
                max_retries,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            last_exception = exc
            logger.warning(
                "Attempt %d/%d failed for flight %s: %s",
                attempt,
                max_retries,
                flight_id,
                exc,
            )
            if attempt < max_retries:
                sleep_seconds = 2 ** (attempt - 1)
                logger.info("Retrying flight %s in %d s", flight_id, sleep_seconds)
                time.sleep(sleep_seconds)
    logger.error(
        "All %d attempts failed for flight %s: %s",
        max_retries,
        flight_id,
        last_exception,
    )
    return False


def _build_igc_url(base_url: str, flight: Flight) -> str:
    if flight.igc_url:
        return urljoin(base_url, flight.igc_url)
    return f"{base_url.rstrip('/')}/flight/{flight.id}/igc"


def main(args: Optional[list[str]] = None) -> int:
    _load_dotenv_if_available()
    parsed = _parse_args(args)

    try:
        username, password = _resolve_credentials(parsed)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    project_root = Path(__file__).resolve().parent.parent
    flights_jsonl = project_root / parsed.flights_jsonl
    output_dir = project_root / parsed.output_dir
    logs_dir = project_root / parsed.logs_dir

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    log_file = logs_dir / f"download_igc_{run_id}.log"
    summary_file = logs_dir / f"download_igc_summary_{run_id}.json"

    logger = _setup_logging(log_file)
    logger.info("Starting download_igc run %s", run_id)
    logger.info("flights_jsonl: %s", flights_jsonl)
    logger.info("output_dir:    %s", output_dir)
    logger.info("logs_dir:      %s", logs_dir)
    logger.info("base_url:      %s", parsed.base_url)
    logger.info("force:         %s", parsed.force)
    logger.info("max_retries:   %d", parsed.max_retries)
    logger.info("rate_limit:    %.1f s", parsed.rate_limit)

    if not flights_jsonl.exists():
        logger.error("Flights file not found: %s", flights_jsonl)
        return 1

    try:
        flights = _read_flights(flights_jsonl)
    except ValueError as exc:
        logger.error("Failed to read flights: %s", exc)
        return 1

    summary = Summary(
        run_id=run_id,
        started_at=datetime.now(timezone.utc).isoformat(),
        total=len(flights),
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        import requests
    except ImportError as exc:
        logger.error("Missing required dependency 'requests': %s", exc)
        return 1

    session = requests.Session()
    session.auth = (username, password)
    session.headers.update({
        "User-Agent": "igc-extractor/1.0 (+https://github.com/Vollol1/igc-extractor)",
        "Accept": "*/*",
    })

    previous_request_time: Optional[float] = None

    for index, flight in enumerate(flights, start=1):
        output_path = output_dir / flight.igc_filename
        logger.info(
            "[%d/%d] Processing flight %s (date=%s, takeoff=%s)",
            index,
            summary.total,
            flight.id,
            flight.date,
            flight.takeoff,
        )

        if not _needs_download(output_path, parsed.force):
            logger.info("Skipping flight %s: %s already exists", flight.id, output_path.name)
            summary.skipped += 1
            continue

        if not parsed.force and output_path.exists() and output_path.stat().st_size == 0:
            logger.info("Removing empty placeholder for flight %s", flight.id)
            output_path.unlink()

        url = _build_igc_url(parsed.base_url, flight)
        logger.info("Downloading flight %s from %s", flight.id, url)

        now = time.monotonic()
        if previous_request_time is not None:
            elapsed = now - previous_request_time
            if elapsed < parsed.rate_limit:
                sleep_for = parsed.rate_limit - elapsed
                logger.debug("Rate limit sleep: %.2f s", sleep_for)
                time.sleep(sleep_for)

        success = _download_with_retry(
            session=session,
            url=url,
            output_path=output_path,
            flight_id=flight.id,
            max_retries=parsed.max_retries,
            logger=logger,
        )
        previous_request_time = time.monotonic()

        if success:
            summary.downloaded += 1
        else:
            summary.failed += 1
            summary.errors.append(
                {
                    "flight_id": flight.id,
                    "url": url,
                    "output_path": str(output_path),
                }
            )

    summary.finished_at = datetime.now(timezone.utc).isoformat()
    summary.write(summary_file)

    logger.info(
        "Run %s finished: total=%d, downloaded=%d, skipped=%d, failed=%d",
        run_id,
        summary.total,
        summary.downloaded,
        summary.skipped,
        summary.failed,
    )
    logger.info("Summary written to %s", summary_file)

    return 0 if summary.failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())

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
import json
import logging
import os
import re
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode, urljoin

import requests

try:
    from tqdm import tqdm  # type: ignore
except ImportError:  # pragma: no cover
    def tqdm(iterable, *args, **kwargs):  # type: ignore[no-redef]
        return iterable

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover
    load_dotenv = None  # type: ignore


DEFAULT_BASE_URL = "https://www.dhv-xc.de"
LOGIN_PATH = "/login"
LOGIN_API_PATH = "/api/xc/login/login"
FLIGHTS_API_PATH = "/api/fli/flights"
IGC_DOWNLOAD_PATH_TEMPLATE = "/flight/{id}/igc"
CSRF_TOKEN_RE = re.compile(r"jc\.token\s*=\s*['\"]([^'\"]+)['\"]")
PAGE_SIZE = 50
TARGET_MIN_FLIGHTS = 200


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


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    if load_dotenv is None:
        return
    dotenv_path = _project_root() / ".env"
    load_dotenv(dotenv_path, override=False)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_csrf_token(html: str) -> str:
    match = CSRF_TOKEN_RE.search(html)
    if not match:
        raise RuntimeError("Could not extract CSRF token (jc.token) from login page")
    return match.group(1)


def _api_url(base_url: str, path: str, params: Optional[dict[str, Any]] = None) -> str:
    url = urljoin(base_url, path)
    if params:
        url += "?" + urlencode(params, doseq=True)
    return url


def _api_headers(csrf_token: str) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "X-Csrf-Token": csrf_token,
        "X-Requested-With": "XMLHttpRequest",
    }


class DhvXcClient:
    """Thin session wrapper around dhv-xc.de's kers.app API."""

    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "igc-extractor/1.0 (private automation; contact: user@example.com)"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "de,en-US;q=0.7,en;q=0.3",
        })
        self.csrf_token: Optional[str] = None

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        files: Optional[dict[str, Any]] = None,
        json_body: Optional[dict[str, Any]] = None,
        allow_redirects: bool = True,
    ) -> requests.Response:
        url = _api_url(self.base_url, path, params)
        headers: dict[str, str] = {}
        if self.csrf_token:
            headers.update(_api_headers(self.csrf_token))
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        resp = self.session.request(
            method,
            url,
            headers=headers,
            data=data,
            files=files,
            json=json_body,
            allow_redirects=allow_redirects,
            timeout=60,
        )
        resp.raise_for_status()
        return resp

    def login(self) -> dict[str, Any]:
        """Authenticate with dhv-xc.de."""
        login_page = self._request("GET", LOGIN_PATH)
        self.csrf_token = _parse_csrf_token(login_page.text)
        logging.info("Fetched login page and CSRF token")

        form_data = {
            "uid": self.username,
            "pwd": self.password,
            "stay": "1",
            "dhvfetch": "0",
        }
        resp = self._request("POST", LOGIN_API_PATH, data=form_data)

        try:
            payload = resp.json()
        except ValueError as exc:
            raise RuntimeError(
                f"Login response was not JSON (status {resp.status_code}). "
                "The API endpoint or login flow may have changed."
            ) from exc

        if not payload.get("success"):
            meta = payload.get("meta", {})
            message = payload.get("message") or meta.get("message") or "Unknown login error"
            code = meta.get("code", 0)
            raise RuntimeError(f"Login failed (code {code}): {message}")

        meta = payload.get("meta", {})
        if "token" in meta:
            self.csrf_token = meta["token"]
            logging.info("CSRF token refreshed by login response")

        logging.info("Login reported success")
        return payload

    def get_flight_page(
        self,
        start: int = 0,
        limit: int = PAGE_SIZE,
    ) -> dict[str, Any]:
        navpars = {
            "start": start,
            "limit": limit,
            "sort": "FlightDate",
            "dir": "desc",
        }
        params: dict[str, Any] = {
            "mine": "1",
            "incpriv": "1",
            "navpars": json.dumps(navpars, separators=(",", ":")),
        }

        resp = self._request("GET", FLIGHTS_API_PATH, params=params)
        try:
            return resp.json()
        except ValueError as exc:
            raise RuntimeError(
                "Flight list response was not JSON. The API may have changed."
            ) from exc


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
        ExtractedAt=_now_iso(),
    )


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
            except json.JSONDecodeError:
                logging.warning("Skipping malformed JSONL line: %s", line[:80])
    return records


def _write_jsonl(path: Path, records: list[FlightRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        for record in records:
            fh.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")


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
        description="List own flights from dhv-xc.de and write them to JSONL.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DHV_XC_BASE_URL", DEFAULT_BASE_URL),
        help="DHV-XC base URL (default: https://www.dhv-xc.de).",
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
    project_root = _project_root()
    output_path = project_root / parsed.output
    log_path = project_root / "data" / "logs" / f"list_flights_{run_id}.log"
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

    existing = _read_jsonl(output_path)
    merged = _merge_idempotent(existing, fetched_records)
    _write_jsonl(output_path, merged)

    logging.info("Wrote %s flight record(s) to %s", len(merged), output_path)
    print(f"Login successful, {len(fetched_records)} flight(s) fetched, "
          f"{len(merged)} record(s) in {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

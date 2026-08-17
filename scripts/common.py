#!/usr/bin/env python3
"""
scripts/common.py

Wiederverwendbare Hilfsfunktionen für die igc-extractor-Skripte.

Dieses Modul wurde als gemeinsame Basis für das Kartenfeature und zukünftige
Tools extrahiert. Es hält bewusst nur abhängigkeitsarme, robuste Utilities,
die in allen Pipeline-Skripten genutzt werden können.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional


_UNSAFE_FILENAME_CHARS = set('\\/:*?"<>|')


def project_root() -> Path:
    """Return the repository root, i.e. the parent directory of ``scripts/``."""
    return Path(__file__).resolve().parent.parent


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """
    Read a JSONL file, returning a list of decoded objects.

    Empty lines are ignored. Malformed lines produce a warning and are skipped,
    matching the lenient behavior of the original scripts.
    """
    if not path.exists():
        return []
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


def write_jsonl(path: Path, records: list[Any]) -> None:
    """
    Write ``records`` to ``path`` as JSONL.

    ``records`` may contain plain dicts or dataclass instances with a
    ``to_dict`` method. Parent directories are created automatically.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        for record in records:
            if hasattr(record, "to_dict"):
                payload = record.to_dict()
            else:
                payload = record
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def sanitize_filename(value: Optional[str]) -> str:
    """Return a printable, filesystem-safe version of ``value``."""
    if value is None:
        return ""
    return "".join(
        c if c not in _UNSAFE_FILENAME_CHARS and c.isprintable() else "_"
        for c in str(value)
    )


def to_int(value: Any) -> Optional[int]:
    """Convert ``value`` to ``int`` or return ``None`` on failure / emptiness."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> Optional[float]:
    """Convert ``value`` to ``float`` or return ``None`` on failure / emptiness."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compute_hashes(data: bytes) -> tuple[str, str]:
    """Return ``(md5_hexdigest, sha256_hexdigest)`` for ``data``."""
    md5 = hashlib.md5(data).hexdigest()
    sha256 = hashlib.sha256(data).hexdigest()
    return md5, sha256


@dataclass(frozen=True, slots=True)
class BRecord:
    """Parsed IGC B-Record (fix)."""

    latitude: float
    longitude: float
    altitude_pressure: Optional[int]
    altitude_gnss: Optional[int]
    time: str
    record_text: str


def _parse_igc_latitude(lat_str: str, lat_sign: str) -> float:
    """Parse IGC latitude (DDMMMMM) and apply sign from N/S."""
    degrees = int(lat_str[:2])
    minutes = float(lat_str[2:]) / 1000.0
    lat = degrees + minutes / 60.0
    return -lat if lat_sign == "S" else lat


def _parse_igc_longitude(lon_str: str, lon_sign: str) -> float:
    """Parse IGC longitude (DDDMMMMM) and apply sign from E/W."""
    degrees = int(lon_str[:3])
    minutes = float(lon_str[3:]) / 1000.0
    lon = degrees + minutes / 60.0
    return -lon if lon_sign == "W" else lon


def _normalize_igc_altitude(alt_str: str) -> Optional[int]:
    """
    Normalize an IGC B-Record altitude field to a 5-digit integer in metres.

    Most loggers encode altitude as a 5-digit metre value, e.g. ``01860``.
    Some loggers emit non-standard encodings:

    * additional fractional digits (``018600`` → ``01860``)
    * an ``A`` marker prefix used by some Flymaster/Skytraxx variants
    * other non-digit noise

    The strategy is therefore lenient: take up to the first five *digits*
    from the field and interpret them as a signed integer. If the resulting
    string is all digits, return it as ``int``; otherwise return ``None``.
    """
    if not alt_str:
        return None

    # Some loggers prefix GNSS altitude with an 'A' marker. Strip a leading
    # 'A' before extracting digits, but keep a possible leading minus sign.
    if alt_str.startswith("A"):
        alt_str = alt_str[1:]

    digits = ""
    for char in alt_str:
        if char.isdigit() or (char == "-" and not digits):
            digits += char
        # Once we have collected at least five digits we can stop; anything
        # beyond that is treated as fractional / logger-specific noise.
        if len(digits.lstrip("-")) >= 5:
            break

    if not digits or digits == "-":
        return None

    # Intentionally tolerate values that may look like they have a sign; IGC
    # altitudes are unsigned metres, but a minus is accepted defensively.
    if digits.lstrip("-").isdigit():
        return int(digits)
    return None


def parse_igc_records(igc_path: Path) -> Iterator[BRecord]:
    """
    Parse B-Records from an IGC file.

    The file is read line by line. The optional A-Record is skipped (but used
    implicitly only to ignore non-fix lines). Each B-Record is decomposed
    according to the IGC specification:

        B HHMMSS DDMMMMM N DDDMMMMM E PPPPP GGGGG AAAAA

    Fields after the 35-character base record are ignored, so the parser is
    robust against logger-specific extensions.

    Some loggers omit the pressure altitude field and emit an ``A`` marker at
    position 24 followed immediately by the 5-digit GNSS altitude. In that
    case the pressure altitude is set to ``None`` and the GNSS altitude is
    parsed from position 24 onwards.

    Yields ``BRecord`` objects. Corrupt B-Records are logged and skipped;
    non-B lines are ignored.
    """
    try:
        text = igc_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logging.warning("Could not read IGC file %s: %s", igc_path, exc)
        return

    for line in text.splitlines():
        if not line.startswith("B"):
            continue
        record = line.rstrip("\r\n")
        # Minimal base length for a valid B-Record according to the spec.
        if len(record) < 35:
            logging.warning("Skipping short B-Record in %s: %s", igc_path, record[:80])
            continue
        try:
            time = record[1:7]
            lat = _parse_igc_latitude(record[7:14], record[14])
            lon = _parse_igc_longitude(record[15:23], record[23])

            # Position 24 is normally the start of the 5-digit pressure
            # altitude. Certain Flymaster/Skytraxx variants place an 'A'
            # marker here and encode only GNSS altitude after it.
            raw_press = record[24:29]
            if raw_press.startswith("A") and record[25:30].isdigit():
                alt_press = None
                alt_gnss = _normalize_igc_altitude(record[24:30])
            else:
                alt_press = _normalize_igc_altitude(raw_press)
                alt_gnss = _normalize_igc_altitude(record[29:34])
        except (ValueError, IndexError) as exc:
            logging.warning("Skipping malformed B-Record in %s: %s", igc_path, exc)
            continue
        yield BRecord(
            latitude=lat,
            longitude=lon,
            altitude_pressure=alt_press,
            altitude_gnss=alt_gnss,
            time=time,
            record_text=record,
        )

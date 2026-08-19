#!/usr/bin/env python3
"""
Generate an interactive Leaflet map of all imported IGC flights.

The script reads ``data/processed/flights.jsonl`` and the associated IGC files in
``data/igc/``. It parses B-Records (Lat/Lon/Altitude/Time) and renders a
self-contained HTML file with:

* Flight tracks as polylines.
* Takeoff markers for each flight.
* Interactive popups with flight details.
* A statistics panel.
* Toggleable layer groups: category (default), takeoff, year, glider.

No external web backend is required; the resulting HTML can be opened directly
in a browser.
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import os
import sqlite3
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from common import (
    BRecord,
    parse_igc_records,
    project_root,
    read_jsonl,
    sanitize_filename,
    to_float,
    to_int,
)
from dhv_xc_client import load_dotenv_if_available


DEFAULT_FLIGHTS_JSONL = Path("data/processed/flights.jsonl")
DEFAULT_IGC_DIR = Path("data/igc")
DEFAULT_DB = Path("data/igc-extractor.db")
DEFAULT_OUTPUT_DIR = Path("data/export")
DEFAULT_LOG_DIR = Path("data/logs")

MAX_TRACK_POINTS = 750

CATEGORY_ORDER = ["XC", "Hoehenflug", "Lokal"]
CATEGORY_RULES: list[tuple[str, str, Callable[["FlightRecord"], bool]]] = [
    (
        "XC",
        "Fluege mit Best-Task-Distanz > 5 km",
        lambda f: f.best_task_distance is not None and f.best_task_distance > 5.0,
    ),
    (
        "Hoehenflug",
        "Fluege mit maximaler Hoehe > 1000 m",
        lambda f: f.max_altitude is not None and f.max_altitude > 1000,
    ),
    ("Lokal", "Uebrige Fluege", lambda f: True),
]

CATEGORY_COLORS = {
    "XC": "#2563eb",
    "Hoehenflug": "#ea580c",
    "Lokal": "#16a34a",
}


def _categorize(flight: "FlightRecord") -> str:
    for key, _label, predicate in CATEGORY_RULES:
        if predicate(flight):
            return key
    return "Lokal"


@dataclass
class FlightRecord:
    """Internal representation of one flight for the map export."""

    id_flight: int
    flight_date: Optional[str]
    takeoff_location: Optional[str]
    glider: Optional[str]
    flight_duration: Optional[int]
    best_task_distance: Optional[float]
    igc_filename: Optional[str]
    valid: Optional[str] = None
    source: dict[str, Any] = field(default_factory=dict)

    # Populated while parsing the IGC file.
    track: list[BRecord] = field(default_factory=list)
    max_altitude: Optional[int] = None
    missing_igc: bool = False
    has_outliers: bool = False
    outlier_count: int = 0

    @property
    def year(self) -> Optional[str]:
        if self.flight_date and len(self.flight_date) >= 4:
            return self.flight_date[:4]
        return None

    @property
    def group_year(self) -> str:
        return self.year or "Unbekanntes Jahr"

    @property
    def group_takeoff(self) -> str:
        return self.takeoff_location or "Unbekannter Startplatz"

    @property
    def group_glider(self) -> str:
        return self.glider or "Unbekannter Gleitschirm"

    @property
    def group_category(self) -> str:
        return _categorize(self)

    @property
    def category_color(self) -> str:
        return CATEGORY_COLORS.get(self.group_category, "#6b7280")

    @property
    def popup_html(self) -> str:
        duration = self.flight_duration
        distance = self.best_task_distance
        max_alt = self.max_altitude
        rows = [
            ("IDFlight", self.id_flight),
            ("FlightDate", self.flight_date or "-"),
            ("TakeoffLocation", self.takeoff_location or "-"),
            ("Glider", self.glider or "-"),
            (
                "FlightDuration",
                f"{duration} min" if duration is not None else "-",
            ),
            (
                "BestTaskDistanceKm",
                f"{distance:.2f} km" if distance is not None else "-",
            ),
            (
                "MaxAltitudeM",
                f"{max_alt} m" if max_alt is not None else "-",
            ),
            ("ValidStatus", self.valid or "unknown"),
            ("TrackPoints", len(self.track)),
        ]
        if self.has_outliers:
            rows.append(("OutlierPoints", f"{self.outlier_count} (filtered)"))
        cells = "".join(
            f"<tr><th>{html.escape(str(label))}</th><td>{html.escape(str(value))}</td></tr>"
            for label, value in rows
        )
        if self.has_outliers:
            warning = "<tr><td colspan='2' style='color:#dc2626;font-weight:600;'>⚠️ Track contains filtered outlier points</td></tr>"
            cells += warning
        return f"<table class='flight-popup'>{cells}</table>"


def _record_altitude(record: BRecord) -> Optional[int]:
    """Return the usable altitude for a B-Record (GNSS preferred)."""
    if record.altitude_gnss is not None:
        return record.altitude_gnss
    return record.altitude_pressure


def _haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    import math
    R = 6371.0  # Earth's radius in km
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _is_valid_coordinate(lat: float, lon: float) -> bool:
    """Check if coordinates are within valid ranges."""
    # Valid latitude: -90 to 90, but exclude extreme poles for glider flights
    if lat < -90 or lat > 90:
        return False
    # Valid longitude: -180 to 180
    if lon < -180 or lon > 180:
        return False
    # Exclude coordinates at 0,0 (Gulf of Guinea - common GPS error)
    if abs(lat) < 0.001 and abs(lon) < 0.001:
        return False
    return True


def _filter_outliers(
    points: list[BRecord],
    max_jump_km: float = 100.0,
) -> tuple[list[BRecord], int]:
    """
    Filter out outlier points from a track.
    
    Returns a tuple of (filtered_points, outlier_count).
    
    Checks:
    - Coordinates must be in valid ranges
    - Consecutive points must not jump more than max_jump_km
    """
    if not points:
        return [], 0
    
    filtered: list[BRecord] = []
    outlier_count = 0
    last_valid: Optional[BRecord] = None
    
    for point in points:
        # Check valid coordinate range
        if not _is_valid_coordinate(point.latitude, point.longitude):
            outlier_count += 1
            continue
        
        # Check for large jumps from last valid point
        if last_valid is not None:
            distance = _haversine_distance_km(
                last_valid.latitude,
                last_valid.longitude,
                point.latitude,
                point.longitude,
            )
            if distance > max_jump_km:
                outlier_count += 1
                continue
        
        filtered.append(point)
        last_valid = point
    
    return filtered, outlier_count


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


def _parse_flight(record: dict[str, Any]) -> FlightRecord:
    flight_id = record.get("IDFlight")
    if flight_id is None:
        raise ValueError("Flight record has no 'IDFlight' field")
    return FlightRecord(
        id_flight=int(flight_id),
        flight_date=record.get("FlightDate") or None,
        takeoff_location=record.get("TakeoffLocation") or None,
        glider=record.get("Glider") or None,
        flight_duration=to_int(record.get("FlightDuration")),
        best_task_distance=to_float(record.get("BestTaskDistance")),
        igc_filename=record.get("IgcFilename") or None,
        source=record,
    )


def _build_flights(
    jsonl_path: Path,
    db_path: Path,
) -> tuple[list[FlightRecord], list[dict[str, Any]]]:
    if not jsonl_path.exists():
        raise FileNotFoundError(f"Flights JSONL not found: {jsonl_path}")

    valid_status = _read_valid_status(db_path)
    raw_records = read_jsonl(jsonl_path)
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
    candidates.append(f"{flight.id_flight}.igc")
    if flight.flight_date and flight.takeoff_location:
        candidates.append(
            f"{flight.id_flight}_{sanitize_filename(flight.flight_date)}_"
            f"{sanitize_filename(flight.takeoff_location)}.igc"
        )

    for candidate in candidates:
        path = igc_dir / candidate
        if path.exists() and path.stat().st_size > 0:
            return path
    return None


def _subsample(points: list[BRecord], max_points: int = MAX_TRACK_POINTS) -> list[BRecord]:
    """Return an evenly subsampled subset of track points."""
    if len(points) <= max_points:
        return points
    step = len(points) / max_points
    return [points[min(int(i * step), len(points) - 1)] for i in range(max_points)]


def _parse_tracks(
    flights: list[FlightRecord],
    igc_dir: Path,
    logger: logging.Logger,
) -> tuple[list[FlightRecord], list[FlightRecord]]:
    """Parse IGC tracks; return (flights_with_track, missing)."""
    with_tracks: list[FlightRecord] = []
    missing: list[FlightRecord] = []
    for flight in flights:
        igc_path = _locate_igc_file(igc_dir, flight)
        if igc_path is None:
            flight.missing_igc = True
            missing.append(flight)
            logger.warning(
                "No local IGC file found for flight %s (tried %s)",
                flight.id_flight,
                flight.igc_filename or f"{flight.id_flight}.igc",
            )
            # Still include the flight for statistics; track will be empty.
            with_tracks.append(flight)
            continue

        records = list(parse_igc_records(igc_path))
        if not records:
            flight.missing_igc = True
            missing.append(flight)
            logger.warning("No B-Records found in IGC file for flight %s", flight.id_flight)
            with_tracks.append(flight)
            continue

        # Filter outliers before subsampling
        filtered_records, outlier_count = _filter_outliers(records)
        if outlier_count > 0:
            flight.has_outliers = True
            flight.outlier_count = outlier_count
            logger.warning(
                "Flight %s: filtered %d outlier points from %d total B-Records",
                flight.id_flight,
                outlier_count,
                len(records),
            )

        flight.track = _subsample(filtered_records)
        flight.max_altitude = max(
            (alt for rec in records if (alt := _record_altitude(rec)) is not None),
            default=None,
        )
        with_tracks.append(flight)
        logger.info(
            "Parsed %d B-Records for flight %s (%d points displayed, %d outliers filtered)",
            len(records),
            flight.id_flight,
            len(flight.track),
            outlier_count,
        )
    return with_tracks, missing


def _format_duration(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours} h {mins} min"
    if hours:
        return f"{hours} h"
    return f"{mins} min"


def _format_distance(km: Optional[float]) -> str:
    if km is None:
        return "-"
    return f"{km:.2f} km"


def _compute_stats(flights: list[FlightRecord]) -> dict[str, Any]:
    total = len(flights)
    flights_with_track = [f for f in flights if f.track]
    flights_without_igc = [f for f in flights if f.missing_igc]
    
    dates = sorted({f.flight_date for f in flights if f.flight_date})
    durations = [f.flight_duration for f in flights if f.flight_duration is not None]
    distances = [f.best_task_distance for f in flights if f.best_task_distance is not None]
    takeoffs = {f.takeoff_location for f in flights if f.takeoff_location}
    gliders = {f.glider for f in flights if f.glider}

    valid_counts: dict[str, int] = {"valid": 0, "invalid": 0, "missing": 0, "unknown": 0}
    for f in flights:
        if f.missing_igc:
            valid_counts["missing"] += 1
        elif f.valid:
            valid_counts[f.valid] = valid_counts.get(f.valid, 0) + 1
        else:
            valid_counts["unknown"] += 1

    # Count outliers across all flights
    total_outliers = sum(f.outlier_count for f in flights)
    flights_with_outliers = sum(1 for f in flights if f.has_outliers)

    best_flight = None
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
        period_label = earliest if earliest == latest else f"{earliest} bis {latest}"
    elif earliest:
        period_label = earliest
    elif latest:
        period_label = latest

    # Category counts based ONLY on flights with actual tracks
    category_counts = {key: 0 for key in CATEGORY_ORDER}
    for f in flights_with_track:
        category_counts[f.group_category] = category_counts.get(f.group_category, 0) + 1

    return {
        "total_flights": total,
        "flights_with_track": len(flights_with_track),
        "flights_without_igc": len(flights_without_igc),
        "flights_with_outliers": flights_with_outliers,
        "total_outliers_filtered": total_outliers,
        "period": {
            "earliest_flight_date": earliest,
            "latest_flight_date": latest,
            "period_label": period_label,
        },
        "total_flight_duration_minutes": sum(durations) if durations else 0,
        "total_flight_duration_formatted": (
            _format_duration(sum(durations)) if durations else "0 min"
        ),
        "sum_xc_distance_km": round(sum(distances), 3) if distances else 0.0,
        "best_single_flight_distance_km": (
            round(best_flight.best_task_distance, 3)
            if best_flight and best_flight.best_task_distance is not None
            else None
        ),
        "best_single_flight": {
            "IDFlight": best_flight.id_flight,
            "FlightDate": best_flight.flight_date,
            "TakeoffLocation": best_flight.takeoff_location,
            "Glider": best_flight.glider,
        } if best_flight else None,
        "unique_takeoff_locations": len(takeoffs),
        "unique_gliders": len(gliders),
        "valid_status_counts": valid_counts,
        "category_counts": category_counts,
    }


def _track_points_geojson(points: list[BRecord]) -> list[list[float]]:
    """Return a GeoJSON-style coordinate list for a polyline."""
    return [[rec.longitude, rec.latitude] for rec in points]


def _build_map_data(
    flights: list[FlightRecord],
    stats: dict[str, Any],
    group_by: str,
) -> dict[str, Any]:
    """Serialize flights and layers into data structures for the HTML template."""
    group_key: Callable[[FlightRecord], str]
    if group_by == "takeoff":
        group_key = lambda f: f.group_takeoff  # noqa: E731
    elif group_by == "year":
        group_key = lambda f: f.group_year  # noqa: E731
    elif group_by == "glider":
        group_key = lambda f: f.group_glider  # noqa: E731
    else:
        group_key = lambda f: f.group_category  # noqa: E731

    grouped: dict[str, list[FlightRecord]] = {}
    for flight in flights:
        key = group_key(flight)
        grouped.setdefault(key, []).append(flight)

    # Keep a deterministic order.
    if group_by == "category":
        ordered_keys = [k for k in CATEGORY_ORDER if k in grouped]
        ordered_keys += sorted(k for k in grouped if k not in CATEGORY_ORDER)
    else:
        ordered_keys = sorted(grouped.keys())

    layers: list[dict[str, Any]] = []
    for key in ordered_keys:
        layer_flights = grouped[key]
        layer_tracks: list[dict[str, Any]] = []
        for flight in layer_flights:
            if flight.track:
                start = flight.track[0]
                layer_tracks.append({
                    "id": flight.id_flight,
                    "color": flight.category_color,
                    "category": flight.group_category,
                    "points": _track_points_geojson(flight.track),
                    "popup": flight.popup_html,
                    "meta": {
                        "flightDate": flight.flight_date or "-",
                        "duration": f"{flight.flight_duration} min"
                        if flight.flight_duration is not None else "-",
                        "distance": f"{flight.best_task_distance:.2f} km"
                        if flight.best_task_distance is not None else "-",
                        "maxAltitude": f"{flight.max_altitude} m"
                        if flight.max_altitude is not None else "-",
                        "takeoff": flight.takeoff_location or "-",
                        "glider": flight.glider or "-",
                        "valid": flight.valid or "unknown",
                        "trackPoints": len(flight.track),
                        "startLat": round(start.latitude, 6),
                        "startLon": round(start.longitude, 6),
                    },
                })
        layers.append({
            "name": key,
            "tracks": layer_tracks,
        })

    return {
        "stats": stats,
        "layers": layers,
        "group_by": group_by,
    }


def _html_page(data: dict[str, Any], pilot_name: str) -> str:
    stats = data["stats"]
    layers = data["layers"]

    # Determine a sensible initial map center from the first track start or default.
    center_lat, center_lon, has_center = 51.1657, 10.4515, False
    for layer in layers:
        if layer["tracks"]:
            start = layer["tracks"][0]["points"][0]
            center_lat, center_lon = start[1], start[0]
            has_center = True
            break

    # Serialize data for the JavaScript part.
    layers_json = json.dumps(layers, ensure_ascii=False)

    valid_counts = stats["valid_status_counts"]
    valid_html = " / ".join(
        f"{key}: {valid_counts.get(key, 0)}"
        for key in ["valid", "invalid", "missing", "unknown"]
    )

    category_html = " / ".join(
        f"{key}: {stats['category_counts'].get(key, 0)}"
        for key in CATEGORY_ORDER
    )

    best_flight = stats.get("best_single_flight")
    best_distance = stats.get("best_single_flight_distance_km")
    best_html = "-"
    if best_flight and best_distance is not None:
        best_html = (
            f"{best_distance:.2f} km "
            f"(ID {best_flight['IDFlight']} am {best_flight['FlightDate']}, "
            f"{best_flight['TakeoffLocation'] or '-'}, {best_flight['Glider'] or '-'})"
        )

    initial_zoom = 10 if has_center else 5

    head = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IGC-Flugkarte</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
  integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
  integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<style>
  html, body {{ margin: 0; padding: 0; height: 100%; font-family: system-ui, -apple-system, sans-serif; }}
  #map {{ height: 100%; width: 100%; }}
  .stats-panel {{
    position: absolute;
    top: 48px;
    right: 10px;
    z-index: 1000;
    background: rgba(255, 255, 255, 0.98);
    border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    padding: 12px 14px;
    max-width: 320px;
    max-height: 50vh;
    overflow-y: auto;
    font-size: 12px;
    line-height: 1.4;
  }}
  .stats-panel h1 {{ margin: 0 0 8px; font-size: 15px; color: #111827; }}
  .stats-panel h2 {{ margin: 10px 0 4px; font-size: 12px; color: #374151; border-bottom: 1px solid #e5e7eb; padding-bottom: 2px; }}
  .stats-panel p {{ margin: 4px 0; color: #4b5563; }}
  .stats-panel table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
  .stats-panel th {{ text-align: left; padding-right: 10px; padding-bottom: 3px; color: #6b7280; font-weight: 600; }}
  .stats-panel td {{ text-align: right; color: #111827; padding-bottom: 3px; }}
  .flight-popup {{ border-collapse: collapse; font-size: 12px; }}
  .flight-popup th {{ text-align: left; padding-right: 10px; color: #6b7280; font-weight: 600; padding-bottom: 4px; }}
  .flight-popup td {{ color: #111827; padding-bottom: 4px; }}
  .leaflet-control-layers {{ z-index: 1001 !important; }}
  .leaflet-control-layers-expanded {{ background: rgba(255, 255, 255, 0.95); }}
  .stats-panel-toggle {{
    position: absolute;
    top: 10px;
    right: 10px;
    z-index: 1002;
    background: rgba(255, 255, 255, 0.98);
    border: 2px solid rgba(0,0,0,0.2);
    border-radius: 6px;
    padding: 8px 12px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    transition: background 0.2s;
  }}
  .stats-panel-toggle:hover {{ background: rgba(240, 240, 240, 0.98); }}
  .stats-panel.collapsed {{ display: none; }}
  .flight-info-panel {{
    position: absolute;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 1000;
    background: rgba(255, 255, 255, 0.98);
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    padding: 16px 20px;
    max-width: 600px;
    min-width: 300px;
    font-size: 13px;
    display: none;
  }}
  .flight-info-panel.visible {{ display: block; }}
  .flight-info-panel h3 {{ margin: 0 0 12px; font-size: 16px; color: #111827; }}
  .flight-info-panel .info-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px 16px;
  }}
  .flight-info-panel .info-item {{ display: flex; flex-direction: column; }}
  .flight-info-panel .info-label {{ font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; }}
  .flight-info-panel .info-value {{ font-size: 14px; color: #111827; font-weight: 500; }}
  .flight-info-panel .close-btn {{
    position: absolute;
    top: 8px;
    right: 12px;
    background: none;
    border: none;
    font-size: 20px;
    cursor: pointer;
    color: #6b7280;
    padding: 0;
    line-height: 1;
  }}
  .flight-info-panel .close-btn:hover {{ color: #111827; }}
  .flight-info-panel h3 .category-badge {{
    display: inline-block;
    margin-left: 8px;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    color: #fff;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    vertical-align: middle;
  }}
  .flight-info-panel .info-grid.three-col {{
    grid-template-columns: repeat(3, 1fr);
  }}
  @media (max-width: 640px) {{
    .stats-panel {{ top: 48px; left: 10px; right: 10px; max-width: none; }}
    .flight-info-panel {{ left: 10px; right: 10px; transform: none; min-width: auto; max-width: none; }}
    .flight-info-panel .info-grid,
    .flight-info-panel .info-grid.three-col {{ grid-template-columns: repeat(2, 1fr); }}
  }}
</style>
</head>"""

    body_top = f"""<body>
<div id="map"></div>
<button class="stats-panel-toggle" id="statsToggle" title="Statistik ein-/ausblenden">📊 Statistik</button>
<div class="stats-panel" id="statsPanel">
  <h1>IGC-Flugkarte</h1>
  <p style="margin:0 0 10px; color:#4b5563;">Pilot: {html.escape(pilot_name) if pilot_name else "nicht angegeben"}</p>

  <h2>Statistik</h2>
  <table>
    <tr><th>Anzahl Fl&uuml;ge</th><td>{stats['total_flights']}</td></tr>
    <tr><th>Fl&uuml;ge mit Track</th><td>{stats['flights_with_track']}</td></tr>
    <tr><th>Fl&uuml;ge ohne IGC</th><td>{stats['flights_without_igc']}</td></tr>
    <tr><th>Fl&uuml;ge mit Outliers</th><td>{stats['flights_with_outliers']}</td></tr>
    <tr><th>Outlier-Punkte</th><td>{stats['total_outliers_filtered']}</td></tr>
    <tr><th>Zeitraum</th><td>{html.escape(stats['period']['period_label'] or '-')}</td></tr>
    <tr><th>Gesamtflugzeit</th><td>{html.escape(stats['total_flight_duration_formatted'])}</td></tr>
    <tr><th>Summe XC-Distanz</th><td>{_format_distance(stats['sum_xc_distance_km'])}</td></tr>
    <tr><th>Bester Flug</th><td>{html.escape(best_html)}</td></tr>
    <tr><th>Startpl&auml;tze</th><td>{stats['unique_takeoff_locations']}</td></tr>
    <tr><th>Gleitschirme</th><td>{stats['unique_gliders']}</td></tr>
    <tr><th>Status</th><td>{html.escape(valid_html)}</td></tr>
  </table>

  <h2>Kategorien</h2>
  <p style="margin:0;">{category_html}</p>
  <p style="margin:8px 0 0; font-size:11px; color:#6b7283;">
    XC = Distanz &gt; 5 km; H&ouml;henflug = max. H&ouml;he &gt; 1000 m; Lokal = Rest.
  </p>
  <p style="margin:8px 0 0; font-size:11px; color:#6b7283;">
    Kategorien z&auml;hlen nur Fl&uuml;ge mit vorhandenem Track.
  </p>
</div>"""

    script = f"""<script>
  const center = [{center_lat}, {center_lon}];
  const map = L.map('map').setView(center, {initial_zoom});

  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 20,
  }}).addTo(map);

  const layersData = {layers_json};
  const overlayLayers = {{}};

  const allTrackLayers = [];
  let selectedPolyline = null;

  function updateLineWeights() {{
    const zoom = map.getZoom();
    // Thin lines at low zoom, slightly thicker when zoomed in.
    let weight;
    if (zoom <= 9) weight = 1.4;
    else if (zoom <= 12) weight = 2.2;
    else if (zoom <= 15) weight = 3.5;
    else weight = 5;
    allTrackLayers.forEach(obj => {{
      if (obj.polyline === selectedPolyline) return;
      obj.polyline.setStyle({{ weight: weight, opacity: 0.85 }});
    }});
  }}

  function highlightFlight(obj) {{
    if (selectedPolyline) {{
      const prev = allTrackLayers.find(o => o.polyline === selectedPolyline);
      if (prev) {{
        selectedPolyline.setStyle({{ color: prev.color, weight: 2, opacity: 0.85, dashArray: null }});
        if (prev.marker) prev.marker.setStyle({{ radius: 4, weight: 1 }});
      }}
    }}
    selectedPolyline = obj.polyline;
    obj.polyline.setStyle({{ color: '#facc15', weight: 6, opacity: 1.0, dashArray: '4, 8' }});
    obj.polyline.bringToFront();
    if (obj.marker) obj.marker.setStyle({{ radius: 8, weight: 3, color: '#facc15', fillColor: '#facc15' }});
    showFlightInfo(obj.track);
  }}

  function clearHighlight() {{
    if (selectedPolyline) {{
      const obj = allTrackLayers.find(o => o.polyline === selectedPolyline);
      if (obj) {{
        obj.polyline.setStyle({{ color: obj.color, weight: 2, opacity: 0.85, dashArray: null }});
        if (obj.marker) obj.marker.setStyle({{ radius: 4, weight: 1, color: obj.color, fillColor: obj.color }});
      }}
      selectedPolyline = null;
    }}
    hideFlightInfo();
  }}

  layersData.forEach(layer => {{
    const group = L.layerGroup();

    layer.tracks.forEach(track => {{
      const points = track.points.map(p => [p[1], p[0]]);
      const polyline = L.polyline(points, {{ color: track.color, weight: 2, opacity: 0.85 }})
        .bindPopup(track.popup)
        .addTo(group);

      const startPoint = points[0];
      const marker = L.circleMarker(startPoint, {{
        radius: 4,
        color: track.color,
        fillColor: track.color,
        fillOpacity: 0.85,
        weight: 1,
      }})
        .bindPopup(track.popup)
        .bindTooltip(track.meta.takeoff || 'Start', {{ permanent: false, direction: 'top' }})
        .addTo(group);

      const trackObj = {{ track: track, polyline: polyline, marker: marker, color: track.color }};
      allTrackLayers.push(trackObj);

      const select = () => highlightFlight(trackObj);
      polyline.on('click', select);
      marker.on('click', select);
      polyline.on('mouseover', e => {{
        if (selectedPolyline !== polyline) {{
          polyline.setStyle({{ weight: 4, opacity: 1.0 }});
        }}
      }});
      polyline.on('mouseout', e => {{
        if (selectedPolyline !== polyline) {{
          updateLineWeights();
        }}
      }});
    }});

    overlayLayers[layer.name + ' (' + layer.tracks.length + ')'] = group;
  }});

  L.control.layers(null, overlayLayers, {{ collapsed: false, position: 'topleft' }}).addTo(map);

  // Default: turn on the first layer, leave others off.
  const keys = Object.keys(overlayLayers);
  if (keys.length > 0) {{
    overlayLayers[keys[0]].addTo(map);
  }}

  // Fit map bounds to all visible tracks if possible.
  const allPoints = layersData.flatMap(l => l.tracks.flatMap(t => t.points.map(p => [p[1], p[0]])));
  if (allPoints.length > 0) {{
    map.fitBounds(allPoints, {{ padding: [20, 20], maxZoom: 14 }});
  }}

  map.on('zoomend', updateLineWeights);
  updateLineWeights();

  // Statistics panel toggle.
  const statsPanel = document.getElementById('statsPanel');
  const statsToggle = document.getElementById('statsToggle');
  if (statsToggle && statsPanel) {{
    let panelVisible = true;
    statsToggle.addEventListener('click', () => {{
      panelVisible = !panelVisible;
      statsPanel.classList.toggle('collapsed', !panelVisible);
      statsToggle.textContent = panelVisible ? '📊 Statistik' : '📊 Statistik';
    }});
  }}

  // Flight info panel handling.
  const infoPanel = document.createElement('div');
  infoPanel.className = 'flight-info-panel';
  infoPanel.innerHTML = `
    <button class="close-btn" aria-label="Schließen">&times;</button>
    <h3>Flug <span id="infoFlightId"></span><span class="category-badge" id="infoCategory"></span></h3>
    <div class="info-grid three-col" id="infoGrid"></div>
  `;
  document.body.appendChild(infoPanel);

  function escapeHtml(text) {{
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }}

  function infoItem(label, value) {{
    return `<div class="info-item"><span class="info-label">${{escapeHtml(label)}}</span><span class="info-value">${{escapeHtml(String(value ?? '-'))}}</span></div>`;
  }}

  function showFlightInfo(track) {{
    const meta = track.meta || {{}};
    const idSpan = infoPanel.querySelector('#infoFlightId');
    const catSpan = infoPanel.querySelector('#infoCategory');
    const grid = infoPanel.querySelector('#infoGrid');
    if (idSpan) idSpan.textContent = `#${{track.id}}`;
    if (catSpan) {{
      catSpan.textContent = track.category || '';
      catSpan.style.backgroundColor = track.color || '#6b7280';
    }}
    grid.innerHTML = [
      infoItem('Datum', meta.flightDate),
      infoItem('Dauer', meta.duration),
      infoItem('Distanz', meta.distance),
      infoItem('max. Höhe', meta.maxAltitude),
      infoItem('Startplatz', meta.takeoff),
      infoItem('Gleitschirm', meta.glider),
      infoItem('Status', meta.valid),
      infoItem('Track-Punkte', meta.trackPoints),
      infoItem('Start-Koordinaten', `${{meta.startLat}}, ${{meta.startLon}}`),
    ].join('');
    infoPanel.classList.add('visible');
  }}

  function hideFlightInfo() {{
    infoPanel.classList.remove('visible');
  }}

  infoPanel.querySelector('.close-btn').addEventListener('click', hideFlightInfo);
  map.on('click', e => {{
    // Click on map background clears the selection.
    if (!e.originalEvent || !e.originalEvent.target.closest('.leaflet-overlay-pane, .leaflet-popup-pane, .flight-info-panel')) {{
      clearHighlight();
    }}
  }});
</script>
</html>"""

    return head + "\n" + body_top + "\n" + script


def _write_html(
    output_path: Path,
    flights: list[FlightRecord],
    group_by: str,
    pilot_name: str,
) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stats = _compute_stats(flights)
    data = _build_map_data(flights, stats, group_by)
    html_text = _html_page(data, pilot_name)
    output_path.write_text(html_text, encoding="utf-8")
    return stats


def _parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="export-flight-map",
        description="Generate an interactive Leaflet map of imported IGC flights.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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
        help="Directory containing the local IGC files (default: data/igc).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for the generated HTML map (default: data/export).",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help="SQLite database path for validation status (default: data/igc-extractor.db).",
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
        type=str,
        default=os.environ.get("PILOT_NAME", ""),
        help=(
            "Name of the pilot to display in the map panel. "
            "Defaults to the PILOT_NAME environment variable; if unset, a generic placeholder is used."
        ),
    )
    parser.add_argument(
        "--group-by",
        type=str,
        choices=("category", "takeoff", "year", "glider"),
        default="category",
        help="Layer grouping (default: category).",
    )
    return parser.parse_args(args)


def _resolve_paths(parsed: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path]:
    root = project_root()
    return (
        root / parsed.flights_jsonl,
        root / parsed.igc_dir,
        root / parsed.output_dir,
        root / parsed.db,
        root / parsed.log_dir,
    )


def main(args: Optional[list[str]] = None) -> int:
    load_dotenv_if_available()
    parsed = _parse_args(args)
    flights_jsonl, igc_dir, output_dir, db, log_dir = _resolve_paths(parsed)

    run_id = parsed.run_id or (
        datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    )
    log_path = log_dir / f"export_flight_map_{run_id}.log"
    summary_path = log_dir / f"export_flight_map_summary_{run_id}.json"
    output_path = output_dir / f"flights_map_{run_id}.html"

    started_at = datetime.now(timezone.utc).isoformat()

    _setup_logging(log_path)
    logger = logging.getLogger(__name__)

    logger.info("Starting export_flight_map run %s", run_id)
    logger.info("flights_jsonl: %s", flights_jsonl)
    logger.info("igc_dir:       %s", igc_dir)
    logger.info("db:            %s", db)
    logger.info("output_dir:    %s", output_dir)
    logger.info("group_by:      %s", parsed.group_by)
    logger.info("pilot_name:    %s", parsed.pilot_name)

    try:
        flights, skipped = _build_flights(flights_jsonl, db)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2

    logger.info("Loaded %d flight record(s) from JSONL", len(flights))
    if skipped:
        logger.warning("Skipped %d malformed record(s)", len(skipped))

    flights, missing = _parse_tracks(flights, igc_dir, logger)

    stats = _write_html(output_path, flights, parsed.group_by, parsed.pilot_name)

    finished_at = datetime.now(timezone.utc).isoformat()
    summary = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "total": len(flights),
        "with_track": sum(1 for f in flights if f.track),
        "missing": len(missing),
        "skipped": len(skipped),
        "output_path": str(output_path),
        "group_by": parsed.group_by,
        "stats": stats,
        "missing_flights": [f.id_flight for f in missing],
        "skipped_records": [
            {"line": s["line"], "reason": s["reason"]} for s in skipped
        ],
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    logger.info("Map written to %s", output_path)
    logger.info(
        "Summary: total=%d, with_track=%d, skipped=%d, missing=%d",
        summary["total"],
        summary["with_track"],
        summary["skipped"],
        summary["missing"],
    )
    logger.info("Summary file: %s", summary_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())

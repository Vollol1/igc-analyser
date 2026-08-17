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


DEFAULT_FLIGHTS_JSONL = Path("data/processed/flights.jsonl")
DEFAULT_IGC_DIR = Path("data/igc")
DEFAULT_DB = Path("data/igc-extractor.db")
DEFAULT_OUTPUT_DIR = Path("data/export")
DEFAULT_LOG_DIR = Path("data/logs")
DEFAULT_PILOT_NAME = "Florian Knab"

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
        cells = "".join(
            f"<tr><th>{html.escape(str(label))}</th><td>{html.escape(str(value))}</td></tr>"
            for label, value in rows
        )
        return f"<table class='flight-popup'>{cells}</table>"


def _record_altitude(record: BRecord) -> Optional[int]:
    """Return the usable altitude for a B-Record (GNSS preferred)."""
    if record.altitude_gnss is not None:
        return record.altitude_gnss
    return record.altitude_pressure


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

        flight.track = _subsample(records)
        flight.max_altitude = max(
            (alt for rec in records if (alt := _record_altitude(rec)) is not None),
            default=None,
        )
        with_tracks.append(flight)
        logger.info(
            "Parsed %d B-Records for flight %s (%d points displayed)",
            len(records),
            flight.id_flight,
            len(flight.track),
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

    category_counts = {key: 0 for key in CATEGORY_ORDER}
    for f in flights:
        category_counts[f.group_category] = category_counts.get(f.group_category, 0) + 1

    return {
        "total_flights": total,
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
        layer_markers: list[dict[str, Any]] = []
        for flight in layer_flights:
            if flight.track:
                layer_tracks.append({
                    "id": flight.id_flight,
                    "color": flight.category_color,
                    "points": _track_points_geojson(flight.track),
                    "popup": flight.popup_html,
                })
                start = flight.track[0]
                layer_markers.append({
                    "id": flight.id_flight,
                    "lat": start.latitude,
                    "lon": start.longitude,
                    "label": flight.takeoff_location or "Start",
                    "popup": flight.popup_html,
                    "color": flight.category_color,
                })
        layers.append({
            "name": key,
            "tracks": layer_tracks,
            "markers": layer_markers,
        })

    return {
        "stats": stats,
        "layers": layers,
        "group_by": group_by,
    }


def _html_page(data: dict[str, Any], pilot_name: str) -> str:
    stats = data["stats"]
    layers = data["layers"]

    # Determine a sensible initial map center from the first marker or default.
    center_lat, center_lon, has_center = 51.1657, 10.4515, False
    for layer in layers:
        if layer["markers"]:
            center_lat = layer["markers"][0]["lat"]
            center_lon = layer["markers"][0]["lon"]
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
    top: 10px;
    right: 10px;
    z-index: 1000;
    background: rgba(255, 255, 255, 0.95);
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.15);
    padding: 14px 18px;
    max-width: 340px;
    max-height: 80vh;
    overflow-y: auto;
    font-size: 13px;
    line-height: 1.45;
  }}
  .stats-panel h1 {{ margin: 0 0 10px; font-size: 16px; color: #111827; }}
  .stats-panel h2 {{ margin: 12px 0 6px; font-size: 13px; color: #374151; border-bottom: 1px solid #e5e7eb; padding-bottom: 2px; }}
  .stats-panel table {{ width: 100%; border-collapse: collapse; }}
  .stats-panel th {{ text-align: left; padding-right: 12px; color: #6b7280; font-weight: 600; }}
  .stats-panel td {{ text-align: right; color: #111827; }}
  .flight-popup {{ border-collapse: collapse; }}
  .flight-popup th {{ text-align: left; padding-right: 10px; color: #6b7280; font-weight: 600; }}
  .flight-popup td {{ color: #111827; }}
</style>
</head>"""

    body_top = f"""<body>
<div id="map"></div>
<div class="stats-panel">
  <h1>IGC-Flugkarte</h1>
  <p style="margin:0 0 10px; color:#4b5563;">Pilot: {html.escape(pilot_name)}</p>

  <h2>Statistik</h2>
  <table>
    <tr><th>Anzahl Fl&uuml;ge</th><td>{stats['total_flights']}</td></tr>
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
</div>"""

    script = f"""<script>
  const center = [{center_lat}, {center_lon}];
  const map = L.map('map').setView(center, {initial_zoom});

  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }}).addTo(map);

  const layersData = {layers_json};
  const overlayLayers = {{}};

  layersData.forEach(layer => {{
    const group = L.layerGroup();

    layer.tracks.forEach(track => {{
      const points = track.points.map(p => [p[1], p[0]]);
      L.polyline(points, {{ color: track.color, weight: 3, opacity: 0.8 }})
        .bindPopup(track.popup)
        .addTo(group);
    }});

    layer.markers.forEach(marker => {{
      L.circleMarker([marker.lat, marker.lon], {{
        radius: 6,
        color: marker.color,
        fillColor: marker.color,
        fillOpacity: 0.9,
        weight: 1,
      }})
        .bindPopup(marker.popup)
        .bindTooltip(marker.label, {{ permanent: false, direction: 'top' }})
        .addTo(group);
    }});

    overlayLayers[layer.name + ' (' + layer.tracks.length + ')'] = group;
  }});

  L.control.layers(null, overlayLayers, {{ collapsed: false }}).addTo(map);

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
</script>
</body>
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
        default=DEFAULT_PILOT_NAME,
        help=f"Name of the pilot to display in the map panel (default: {DEFAULT_PILOT_NAME}).",
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

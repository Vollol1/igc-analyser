# Session-Status: igc-extractor — Kartenfeature Iteration

**Datum/Uhrzeit:** 18.08.2026

---

# Runde 1: Kartendarstellung grundlegend fixen

## Probleme

- OpenStreetMap-Tiles blockieren `file://`-Zugriffe (403, Referer required).
- Statistik-Panel überlappt den Viewport, nicht scrollbar.
- Tracks kaum sichtbar.
- Layer-Control nicht sichtbar / hinter Panel verdeckt.

## Umgesetzte Fixes

- Tile-Layer auf CartoDB Positron umgestellt.
- Panel responsive gemacht (`max-height: 50vh`, scrollbar).
- Polylinien deutlicher (`weight: 4`, `opacity: 0.85`).
- Layer-Control nach links oben verschoben, z-Index erhöht.

## Validierung

- `python3 -m py_compile scripts/export_flight_map.py` ✅
- `export_flight_map.py` läuft durch und erzeugt HTML ✅

---

# Runde 2: Nutzer-Feedback nach visuellem Test

## Beobachtete Probleme

### 1. Kategorie-Zählung inkonsistent

- Statistik-Panel zeigt 306 Flüge (alle JSONL-Einträge).
- Layer-Control zeigt nur 200 kategorisierte Tracks (die mit lokaler IGC-Datei).
- Kategorie-Summe im Panel und Layer-Control passen nicht zusammen.

### 2. Marker / Track-Punkte zu groß

- Große grüne/blaue Kreise überdecken die Track-Linien.
- Nur bei starkem Zoom sind die eigentlichen Tracks erkennbar.

### 3. Ausreißer-Tracks durch fehlerhafte IGC-Punkte

- Beispiel: Track von "Bach, Reutte, Tirol" zieht sich bis zum Äquator/Golf von Guinea.
- Ursache: fehlerhafte B-Records mit Null-/ungültigen Koordinaten.

---

# Runde 3: Task `09eb5` — Fixes implementiert

## Umgesetzte Änderungen

### Kategorie-Zählung konsistent

- `_compute_stats()` zählt Kategorien nur noch über `flights_with_track`.
- Statistik-Panel zeigt zusätzlich:
  - `Flüge mit Track: 200`
  - `Flüge ohne IGC: 106`
  - `Flüge mit Outliers: 6`
  - `Outlier-Punkte: 83`
- Layer-Control: `XC (91) / Höhenflug (36) / Lokal (73)` = 200 ✅

### Marker und Tracks dezenter

- `circleMarker` Radius: `6 → 3`
- `fillOpacity`: `0.9 → 0.7`
- Polyline `weight`: `4 → 5`
- Polyline `opacity`: `0.85 → 0.9`

### IGC-Ausreißer filtern und markieren

- Neue Hilfsfunktionen:
  - `_haversine_distance_km()` für Sprung-Check
  - `_is_valid_coordinate()` filtert 0,0-Koordinaten und Werte außerhalb ±90°/±180°
  - `_filter_outliers()` entfernt Punkte mit Sprüngen > 100 km
- `FlightRecord` hat neue Felder `has_outliers` und `outlier_count`.
- Popups markieren betroffene Flüge mit rotem Warnhinweis.

## Validierung

```bash
python3 -m py_compile scripts/export_flight_map.py
# ✅ OK

./scripts/export_flight_map.py --run-id review_09eb5
# ✅ Summary: total=306, with_track=200, missing=106,
#    flights_with_outliers=6, total_outliers_filtered=83
```

---

# Bekannte Einschränkungen / Nächste Schritte

- 106 Flüge haben noch keine lokale IGC-Datei (nur 200 von 306 heruntergeladen).
- Track-Subsampling auf 750 Punkte bleibt unverändert.
- Internetverbindung für Tile-Loading weiterhin erforderlich.

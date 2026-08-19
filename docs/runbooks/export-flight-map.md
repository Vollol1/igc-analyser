# Runbook: Interaktive IGC-Flugkarte erzeugen

Dieses Runbook beschreibt, wie du mit `scripts/export_flight_map.py` eine lokale,
interaktive Karte aller importierten IGC-Flüge erzeugst. Die Karte ist eine
eigenständige HTML-Datei, die direkt im Browser geöffnet werden kann.

## Voraussetzungen

* `data/processed/flights.jsonl` liegt vor (z. B. durch `scripts/list_flights.py`).
* Die zugehörigen `.igc`-Dateien liegen in `data/igc/` (z. B. durch
  `scripts/download_igc.py` oder `scripts/igc_extractor.py`).
* Optional: `data/igc-extractor.db` enthält den strukturellen Validierungsstatus
  (wird durch `scripts/import_flights.py` angelegt).
* Das virtuelle Environment ist aktiviert (siehe [Quick Start](../quickstart.md)).

## Standard-Aufruf

```bash
python scripts/export_flight_map.py
```

Ohne weitere Parameter werden folgende Defaults verwendet:

* `flights.jsonl`: `data/processed/flights.jsonl`
* IGC-Dateien: `data/igc/`
* SQLite-DB: `data/igc-extractor.db`
* Ausgabe: `data/export/flights_map_<run_id>.html`
* Log: `data/logs/export_flight_map_<run_id>.log`
* Summary: `data/logs/export_flight_map_summary_<run_id>.json`
* Gruppierung: `category` (Kategorie-Layer)
* Pilotenname: Umgebungsvariable `PILOT_NAME` (oder neutraler Platzhalter, falls nicht gesetzt)

## Aufrufbeispiele

### Gruppierung nach Startplatz

```bash
python scripts/export_flight_map.py --group-by takeoff
```

### Gruppierung nach Flugjahr

```bash
python scripts/export_flight_map.py --group-by year
```

### Gruppierung nach Gleitschirm

```bash
python scripts/export_flight_map.py --group-by glider
```

### Explizite Pfade und Pilotenname

```bash
python scripts/export_flight_map.py \
  --flights-jsonl data/processed/flights.jsonl \
  --igc-dir data/igc/ \
  --output-dir data/export/ \
  --db data/igc-extractor.db \
  --pilot-name "Max Mustermann" \
  --group-by category \
  --run-id 20260817_export
```

## Layer / Gruppierungen erklärt

Die Karte zeigt grundsätzlich **Tracks** (Polylinien) und **Startplatz-Marker**
für jeden Flug. Rechts oben befindet sich ein festes Layer-Control, mit dem
eine Gruppierung ausgewählt werden kann. Pro Gruppierung wird jeweils genau
eine der folgenden Aufteilungen als umschaltbare Layer angeboten:

| `--group-by` | Bedeutung | Besonderheit |
|---|---|---|
| `category` (Default) | **Lokal / XC / Höhenflug** | Ein Flug landet in der ersten passenden Kategorie: XC wenn `BestTaskDistance > 5 km`; sonst Höhenflug wenn maximale Höhe > 1000 m; sonst Lokal. |
| `takeoff` | **Startplatz** | Jeder eindeutige `TakeoffLocation` wird ein eigener Layer. |
| `year` | **Flugjahr** | Flüge werden nach `FlightDate` (Jahr) gruppiert. |
| `glider` | **Gleitschirm** | Flüge werden nach `Glider` gruppiert. |

> Hinweis: Es wird jeweils eine Gruppierungs-Dimension auf einmal aktiv
> angezeigt. Die Layer-Control erlaubt es, einzelne Gruppen ein- und
> auszuschalten, aber nicht mehrere Gruppierungen gleichzeitig zu mischen.

## Interaktive Elemente

* **Klick auf einen Track oder Marker** öffnet ein Popup mit Flugdetails:
  `IDFlight`, `FlightDate`, `TakeoffLocation`, `Glider`, `FlightDuration`,
  `BestTaskDistanceKm`, `MaxAltitudeM`, `ValidStatus` und Anzahl dargestellter
  Trackpunkte.
* **Statistik-Panel** oben rechts zeigt Anzahl Flüge, Zeitraum,
  Gesamtflugzeit, Summe XC-Distanz, besten Flug, Anzahl Startplätze,
  Gleitschirme und die Zählung `valid / invalid / missing / unknown`.

## Performance

* Tracks werden auf maximal **750 Punkte pro Flug** subsampled, um die
  HTML-Dateigröße und Browser-Rendering-Zeit zu begrenzen.
* Die maximale Höhe pro Flug wird trotz Subsampling aus allen B-Records
  berechnet, damit die Kategorie "Höhenflug" korrekt bleibt.

## Kartenhintergrund

Die Karte verwendet **Leaflet 1.9.4** und CartoDB Positron-Tiles (heller,
neutraler Hintergrund), die aus dem öffentlichen CDN von `basemaps.cartocdn.com`
geladen werden. Die Tiles sind kompatibel mit dem Öffnen der HTML-Datei über
`file://` im Browser. Eine Internetverbindung ist erforderlich, sofern der
Browser die Tiles noch nicht gecacht hat.

Die OpenStreetMap-Attribution bleibt erhalten, da CartoDB die OSM-Daten nutzt.

## Ausgabe-Dateien

Ein Lauf schreibt:

* `data/export/flights_map_<run_id>.html` – die interaktive Karte.
* `data/logs/export_flight_map_<run_id>.log` – detailliertes Log.
* `data/logs/export_flight_map_summary_<run_id>.json` – Zusammenfassung mit
  Statistik, Gruppierung, fehlenden Flügen und ausgelassenen Datensätzen.

## Fehlersuche

* **Keine Flüge auf der Karte**: Prüfe, ob `flights.jsonl` existiert und
  `IDFlight`-Felder enthält.
* **Keine Tracks sichtbar**: Prüfe, ob die `.igc`-Dateien in `data/igc/`
  vorhanden sind und B-Records enthalten. Das Log listet fehlende Dateien
  auf (`missing_flights` im Summary).
* **Falsche Kategorisierung**: Die maximale Höhe wird aus GNSS-Höhe
  bevorzugt, sonst aus Druckhöhe berechnet. Für Höhenflug-Kategorie ist
  `max. Höhe > 1000 m` nötig.

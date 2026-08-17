# Refactoring: Gemeinsames Hilfsmodul `scripts/common.py`

**Datum:** 2026-08-17

## Hintergrund

Vorbereitung für das Kartenfeature (`scripts/export_flight_map.py`). Mehrere
bestehende Skripte enthielten identische oder nahezu identische
Hilfsfunktionen (JSONL-Lesen/-Schreiben, Dateinamens-Sanitizing,
Konvertierungsfunktionen, Hashing). Diese wurden in ein gemeinsames Modul
extrahiert, um Duplikation zu vermeiden und den zukünftigen B-Record-Parser
wiederverwendbar zu machen.

## Entstandene Datei

- `scripts/common.py`
  - `project_root() -> Path`
  - `read_jsonl(path) -> list[dict[str, Any]]`
  - `write_jsonl(path, records)`
  - `sanitize_filename(value) -> str`
  - `to_int(value) -> Optional[int]`
  - `to_float(value) -> Optional[float]`
  - `compute_hashes(data: bytes) -> tuple[str, str]`
  - `parse_igc_records(igc_path: Path) -> Iterator[BRecord]`
    - Robuster B-Record-Parser gemäß IGC-Spezifikation (35 Zeichen
      Basisdatensatz; optionale A-Record-Behandlung durch Überspringen).

## Refactorte Skripte

| Skript                  | Ersetzte Hilfsfunktionen                      |
|-------------------------|-----------------------------------------------|
| `scripts/list_flights.py`   | `_project_root`, `_read_jsonl`, `_write_jsonl` |
| `scripts/download_igc.py`   | `_sanitize_filename`                          |
| `scripts/igc_extractor.py`  | `_project_root`, `_read_jsonl`, `_write_jsonl`, `_sanitize_filename` |
| `scripts/import_flights.py` | `read_jsonl`, `_to_int`, `_to_float`, `compute_hashes` |
| `scripts/export_igc_zip.py` | `_read_jsonl`, `_to_int`, `_to_float`, `_FilenameSanitizer` |

## Verhaltenserhalt

- `read_jsonl` ignoriert leere Zeilen und überspringt beschädigte Zeilen mit
  Warnung (inklusive Zeilennummer, wo sinnvoll).
- `write_jsonl` akzeptiert sowohl `dict`-Records als auch Objekte mit
  `to_dict()` (z. B. `FlightRecord` aus `list_flights.py`).
- `sanitize_filename` verwendet die gleiche Zeichenmenge und das gleiche
  Ersetzungszeichen wie bisher.
- `to_int` / `to_float` behandeln `None` und leere Strings wie bisher als
  `None`.
- `compute_hashes` liefert weiterhin `("md5:<hex>|sha256:<hex>")`-kombinierten
  Hash in `import_flights.py`.

## Validierung

- `python -m py_compile` auf allen geänderten `.py`-Dateien erfolgreich.
- `--help`-Aufrufe aller refactorten Skripte liefern weiterhin die erwartete
  Ausgabe.
- Smoke-Test mit `data/processed/flights.jsonl` bestätigt, dass JSONL-Lesen
  und -Schreiben weiterhin funktioniert (Dry-Run von `igc_extractor.py`).

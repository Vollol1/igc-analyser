# Bugfix-Session: `project_root`-Typfehler in `scripts/igc_extractor.py`

**Datum/Uhrzeit:** 2026-08-18

## Beobachtetes Problem

Nach erfolgreichem Durchlauf von `list_flights.py` stürzte `scripts/igc_extractor.py`
ab mit:

```text
TypeError: unsupported operand type(s) for /: 'function' and 'str'
```

## Ursache

In `scripts/common.py` ist `project_root` als Funktion definiert:

```python
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent
```

`scripts/igc_extractor.py` importierte diese Funktion, verwendete sie aber an
mehreren Stellen ohne Aufruf (`()`) als `Path`-Objekt. Das führte dazu, dass der
Python-Interpreter versuchte, eine Funktion mit einem String zu dividieren –
was den obigen `TypeError` erzeugte.

Betroffene Stellen (vor dem Fix):

- `_run_subprocess`, `_run_list_flights`, `_run_download_igc`,
  `_run_import_flights` hatten einen Parameter namens `project_root: Path`, der
  den importierten Funktionsnamen überschattete.
- In `main()` wurden nach `root = project_root()` trotzdem noch die Zeilen
  `project_root / "data" / ...` verwendet, wodurch der globale Name (die
  Funktion) anstelle des lokalen `root`-Pfads genutzt wurde.

## Durchgeführter Fix

1. In `scripts/igc_extractor.py`:
   - Einmalig `root = project_root()` aufrufen.
   - Den Parameter `project_root: Path` in den Helferfunktionen in `root: Path`
     umbenennen, damit der Funktions-Import nicht mehr überschattet wird.
   - Alle Pfad-Konkatenationen auf das lokale `root`-Objekt umstellen.

2. Konsistenz-Check: Es gibt nun keine Stelle mehr in `igc_extractor.py`, an der
   `project_root` ohne Klammern als Pfad verwendet wird.

## Validierung

```bash
# Syntaktische Korrektheit
python3 -m py_compile scripts/igc_extractor.py

# Hilfeausgabe (kein Netzwerk-/Download-Start)
./scripts/igc_extractor.py --help
```

Beide Checks waren erfolgreich. Ein vollständiger Download wurde nicht
durchgeführt.

## Betroffene Dateien

- `scripts/igc_extractor.py`
- `docs/TODO.md`
- `docs/notes/igc-extractor-project-root-bugfix-2026-08-18.md` (diese Datei)

## Follow-up-Risiken

- `scripts/export_igc_zip.py` und `scripts/dhv_xc_client.py` verwenden jeweils
  ihre eigene lokale `_project_root()`-Funktion; das ist konsistent, aber eine
  künftige Refactoring-Session könnte prüfen, ob alle Skripte den Import aus
  `common.project_root()` nutzen sollten.
- Der Fehler zeigt, dass gleichnamige Parameter und Imports leicht zu
  Laufzeitfehlern führen können. Zukünftige Code-Reviews sollten darauf achten,
  Funktions-Imports nicht durch lokale Variablen/Parameter zu überschatten.

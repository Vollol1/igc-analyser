> [!TIP]
> Vor jedem Lauf prüfe:
> - [ ] `data/processed/flights.jsonl` ist aktuell.
> - [ ] `data/igc/` enthält die zu exportierenden IGC-Dateien.
> - [ ] Optional: `data/igc-extractor.db` ist vorhanden, damit der Validierungsstatus in `flights.csv` landet.
> - [ ] Zielverzeichnis `data/export/` existiert oder wird automatisch angelegt.
> - [ ] Generierte Archive (`*.zip`, `*.tar.gz`) nicht in Git committen — sie stehen in `.gitignore`.

# Runbook: IGC-Dateien als ZIP exportieren

Schritt-für-Schritt-Anleitung für den Export aller lokalen IGC-Dateien inklusive
Metadaten und Validierungsstatus in ein strukturiertes Archiv.

---

## 1. Voraussetzungen

1. Repository liegt lokal vor:
   ```bash
   cd /home/florian/git.vollol.com/fknab/igc-extractor
   ```

2. Virtuelles Environment ist vorhanden:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Die IGC-Dateien wurden heruntergeladen und importiert (siehe [`download-igc.md`](./download-igc.md)).

---

## 2. Standard-Export durchführen

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/export_igc_zip.py
```

Eingaben:

- `data/processed/flights.jsonl` – Flugmetadaten.
- `data/igc/*.igc` – Lokale IGC-Dateien.
- `data/igc-extractor.db` – SQLite-DB mit Validierungsstatus (optional, aber empfohlen).

Ausgaben:

- `data/export/igc_export_<run_id>.zip` – Archiv mit `README.txt`, `export_meta.json`, `flights.csv` und allen IGC-Dateien.
- Log unter `data/logs/export_igc_zip_<run_id>.log`.
- Summary unter `data/logs/export_igc_zip_summary_<run_id>.json`.

---

## 3. Archivinhalt prüfen

```bash
unzip -l data/export/igc_export_<run_id>.zip
```

Der erste Eintrag sollte sein:

1. `README.txt` – Deckblatt mit Piloten-/Absendername, Erstellungsdatum, Anzahl Flüge und Zeitraum.

Danach folgen:

2. `export_meta.json` – Übersichtsstatistik.
3. `flights.csv` – Detaillierte Flugtabelle.

Anschließend die IGC-Dateien in der Form:

```
<IDFlight>_<FlightDate>_<TakeoffLocation>.igc
```

### Meta-Datei ansehen

```bash
unzip -p data/export/igc_export_<run_id>.zip export_meta.json | python3 -m json.tool
```

Enthaltene Felder:

- `total_flights` – Anzahl Flüge im Archiv.
- `total_igc_files` – Gesamtanzahl IGC-Dateien.
- `total_flight_duration_minutes` – Summe der Flugdauern.
- `total_best_task_distance_km` – Summe der Best-Task-Distanzen.
- `period.earliest_flight_date` / `period.latest_flight_date` – Zeitspanne.
- `unique_takeoff_locations` – Anzahl unterschiedlicher Startplätze.
- `generated_at` – Erstellungsdatum.
- `validation_note` – Hinweis auf strukturelle Validierung.

### Flugtabelle ansehen

```bash
unzip -p data/export/igc_export_<run_id>.zip flights.csv | head -n 20
```

Spalten:

- `IDFlight`
- `FlightDate`
- `TakeoffLocation`
- `LandingLocation`
- `Glider`
- `FlightDuration` (Minuten)
- `BestTaskDistance` (km)
- `IgcFilenameInArchive`
- `ValidStatus` (`valid`, `invalid`, `missing` oder `unknown`)
- `OriginalIgcFilename`

---

## 4. Optionen

### Eigener Archivname

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/export_igc_zip.py \
  --output-name meine_fluege_2024.zip
```

### Alternativ tar.gz

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/export_igc_zip.py \
  --format tar.gz
```

### Piloten- / Absendernamen ändern

Standardmäßig wird `README.txt` mit dem Namen `Florian Knab` erzeugt.

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/export_igc_zip.py \
  --pilot-name "Max Mustermann"
```

`--sender` ist ein Alias für `--pilot-name`.

### README.txt prüfen

```bash
unzip -p data/export/igc_export_<run_id>.zip README.txt
```

### Pfade überschreiben

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/export_igc_zip.py \
  --igc-dir /pfad/zu/igc \
  --flights-jsonl /pfad/zu/flights.jsonl \
  --db /pfad/zu/igc-extractor.db \
  --output-dir /pfad/zum/export
```

---

## 5. Fehlerbehebung

| Symptom | Mögliche Ursache | Lösung |
|---------|------------------|--------|
| `missing` in Summary | IGC-Datei fehlt in `data/igc/` | Erneut `download_igc.py` laufen lassen |
| `ValidStatus` = `unknown` | SQLite-DB fehlt oder wurde nicht importiert | `import_flights.py` ausführen |
| Archiv ist leer | `flights.jsonl` leer oder fehlt | `list_flights.py` erneut ausführen |

---

## 6. Checkliste nach dem Export

- [ ] `data/export/igc_export_<run_id>.zip` ist vorhanden und lesbar.
- [ ] `export_meta.json` enthält die erwarteten Werte.
- [ ] `flights.csv` enthält alle erwarteten Spalten und Zeilen.
- [ ] Anzahl IGC-Dateien im Archiv stimmt mit `total_igc_files` überein.
- [ ] Keine `.env` oder Log-Dateien wurden committet.
- [ ] Generierte Archive (`data/export/*.zip`, `data/export/*.tar.gz`) wurden nicht committet.

---

## Verwandte Dokumente

- [Agent-Verhaltensregeln](../../AGENT_BEHAVIOR_NOTES.md)
- [Download-Runbook](./download-igc.md)
- [Pipeline-Notizen](../notes/pipeline-notes.md)
- [ADR-001: Architecture & Tech Stack](../decisions/ADR-001-architecture-techstack.md)

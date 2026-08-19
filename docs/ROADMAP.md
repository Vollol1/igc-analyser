# igc-extractor Roadmap

Diese Roadmap beschreibt die geplante Weiterentwicklung von igc-extractor.
Sie ist in Semantic-Versioning-Releases gegliedert und dient als Orientierung für Kanban-Tasks und ADRs.

Die Roadmap wird bei jedem größeren Feature oder Release aktualisiert.

---

## Status-Legende

- `[-]` in Planung / in Arbeit
- `[x]` released
- `[!]` blockiert / wartet auf Abhängigkeit

---

## v0.4.0 — Öffentliches Release: Cleanup, Disclaimer & CI-Grundgerüst (released 2026-08-19)

**Ziel:** Das Repository für einen öffentlichen GitHub-Release vorbereiten: persönliche
Daten aus dem Code und den Docs entfernen, Brand-Neutralität herstellen, Nutzer über
das Risiko informieren und ein CI-Grundgerüst bereitstellen.

### Released Changes

- [x] Public-release cleanup
  - Persönlicher Default-Pilotenname (`Florian Knab`) aus `scripts/export_flight_map.py` und `scripts/export_igc_zip.py` entfernt.
  - Piloten-/Absendername jetzt über Umgebungsvariable `PILOT_NAME` und CLI-Parameter `--pilot-name` / `--sender` konfigurierbar.
  - Absolute lokale Pfade (`/home/florian/...`) in Code, Runbooks und Notizen durch relative/neutrale Referenzen ersetzt.
  - CLI-Descriptions und Docstrings brand-neutral auf "supported flight-data platform" umgestellt.
- [x] Disclaimer & Kommunikation
  - Prominenter Disclaimer-Block in `README.md` (inoffizielles Tool, Nutzung auf eigene Gefahr, möglicher Account-Bann).
  - Non-blocking Startup-Disclaimer in `scripts/igc_extractor.py`, `scripts/list_flights.py` und `scripts/download_igc.py`.
  - ADR-003 und `docs/notes/legal-release-notes.md` dokumentieren die rechtliche Einschätzung.
- [x] Dokumentation
  - Neues `docs/runbooks/quickstart.md` für einen kompakten Einstieg.
  - Runbooks (`download-igc.md`, `export-igc.md`, `export-flight-map.md`) auf relative Befehle und neutrale `PILOT_NAME`-Defaults aktualisiert.
- [x] CI-Grundgerüst
  - `.github/workflows/ci.yml` mit `py_compile` aller Skripte und `pytest`-Template hinzugefügt.

### Nicht in v0.4.0 umgesetzt (verschoben)

Die folgenden Themen aus dem ursprünglichen [Unreleased]-Bereich bleiben für zukünftige Releases bestehen:

- Testsuite aufbauen (`tests/`).
- Resume-Logik für fehlgeschlagene Downloads verbessern.
- SQLite-Datenbanken konsolidieren.
- `LandingLocation` aus der DHV-XC Detailseite scrapen.
- Validierungs- und Ausreißer-Checks für Flugdaten.
- Höhenflug-Nachweis (optional; siehe v0.5.0+).

---

## v0.2.1 — Bugfix: Import-Datenbank-Pfad (released 2026-08-17)

**Ziel:** Einen Bug korrigieren, bei dem der Orchestrator `scripts/igc_extractor.py` `scripts/import_flights.py` versehentlich die Downloader-State-DB (`data/igc_extractor.db`) statt der Analyse-DB (`data/igc-extractor.db`) übergeben hat. Zusätzlich Bereinigung der daraus entstandenen versehentlichen Tabellen in der State-DB.

### Released Changes

- [x] `scripts/igc_extractor.py` übergibt `--db` jetzt korrekt als `data/igc-extractor.db`.
  - `--state-db` bleibt `data/igc_extractor.db` für Downloader-Resume/Idempotenz.
  - `export_igc_zip.py` liest den Validierungsstatus jetzt aus der korrekten DB.
- [x] Dokumentation korrigiert (`README.md`, `docs/runbooks/download-igc.md`).
- [x] Datenbank-Incident dokumentiert (`docs/notes/pipeline-notes.md`).

---

## v0.2.0 — IGC-Export & Dokumentation (released 2026-08-16)

**Ziel:** Die bestehende Pipeline um einen reproduzierbaren, lokalen IGC-Export erweitern, der für Vereins-/Lizenz-Zwecke (z. B. Höhenflug-Nachweis) genutzt werden kann. Zusätzlich wird die Projekt-Dokumentation konsolidiert.

### Released Changes

- [x] IGC-Export-Modul (`scripts/export_igc_zip.py`)
  - ZIP/tar.gz-Archive mit sprechenden IGC-Dateinamen.
  - `README.txt` Deckblatt mit Piloten-/Absendernamen.
  - `export_meta.json` Übersichtsstatistik (inkl. korrigierter Distanz-Felder).
  - `flights.csv` detaillierte Flugtabelle inkl. Validierungsstatus.
  - `flight_summary.pdf` strukturierte PDF-Zusammenfassung via `reportlab`.
- [x] Korrektur der Meta-Distanz-Felder in `export_meta.json`.
- [x] `LandingLocation` aus dem Export entfernt (wird zukünftig über Detailseite gescraped).
- [x] Dokumentationskonsolidierung (`README.md`, `ROADMAP.md`, `TODO.md`, Agent-Notes, Runbooks).

### Nicht in v0.2.0 umgesetzt (verschoben)

Die folgenden technischen Schulden-/Robustheitsthemen aus der ursprünglichen v0.2.0-Planung wurden nicht umgesetzt und sind im Abschnitt [Unreleased] / Nächstes Release nachzuvollziehen:

- Testsuite aufbauen.
- Resume-Logik für fehlgeschlagene Downloads verbessern.
- SQLite-Datenbanken konsolidieren.

### Motivation

v0.1.0 hat bewiesen, dass die Kernpipeline funktioniert (288 eigene Flüge, 287/288 valid).
v0.2.0 liefert nun einen praxistauglichen Export inkl. menschen- und maschinenlesbarer Begleitdateien.

---

## v0.3.0 — Interaktive IGC-Flugkarte (released 2026-08-18)

**Ziel:** Aus den lokalen IGC-Flugdaten eine eigenständige, interaktive HTML-Karte erzeugen, die Startplätze,
Flugtrajektorien und Statistiken darstellt und direkt im Browser nutzbar ist.

### Released Changes

- [x] Neues Skript `scripts/export_flight_map.py`
  - Liest `data/processed/flights.jsonl` und die zugehörigen IGC-Dateien aus `data/igc/`.
  - Parst B-Records (Breite, Länge, Höhe) aus den IGC-Dateien.
  - Erzeugt eine Leaflet-basierte HTML-Karte mit CartoDB Positron-Hintergrund.
- [x] Karteninhalte
  - Tracks als farbige Polylinien, kategorisiert nach XC / Höhenflug / Lokal.
  - Startplatz-Marker mit Tooltips und Popups.
  - Statistik-Panel mit Fluganzahl, Zeitraum, Gesamtflugzeit, XC-Distanz, bestem Flug, Startplätzen, Gleitschirmen und Validierungsstatus.
  - Zoom-abhängige Linienstärke (1.4–5) für bessere Sichtbarkeit.
  - Ein-/ausklappbares Statistik-Panel mit Toggle-Button.
  - Flug-Highlighting bei Klick/Hover mit separatem Info-Panel für Meta-Infos.
  - Outlier-Erkennung filtert fehlerhafte Koordinaten und markiert betroffene Flüge.
- [x] Umschaltbare Layer-Gruppen
  - **Kategorie** (Default): XC / Höhenflug / Lokal.
  - **Startplatz**, **Flugjahr**, **Gleitschirm** als zusätzliche Layer.
- [x] Output-Dateien
  - `data/export/flights_map_<run_id>.html`
  - `data/logs/export_flight_map_<run_id>.log`
  - `data/logs/export_flight_map_summary_<run_id>.json`
- [x] Bugfix: `--flights` Default in `igc_extractor.py` von 200 auf None geändert

### Bekannte Einschränkungen

- 106 von 306 Flügen hatten zum Release-Zeitpunkt keine lokale IGC-Datei. Nach Ausführen von `./scripts/igc_extractor.py` werden alle fehlenden IGCs nachgeladen.
- 6 Flüge enthielten outlier-Punkte (insgesamt 83), die automatisch gefiltert werden.

### Motivation

Die bisherigen Exports sind tabellarisch oder archivbasiert.
Eine interaktive Karte macht räumliche Muster (Startplatz-Cluster, Fluggebiete, häufige Routen) sofort sichtbar
und dient gleichzeitig als persönliche Flugretrospektive.

### Technische Hinweise

- Leaflet + CartoDB Positron; reine Python-Generierung, kein Web-Backend nötig.
- B-Record-Parser und Outlier-Filter in `export_flight_map.py` implementiert.
- 3D-Ansicht vorgemerkt für spätere Releases.

---

## v0.4.0 — Import aus weiteren Quellen & erweiterte Visualisierung

**Ziel:** Weitere Datenquellen anbinden und die Darstellung der importierten Flüge über die Basis-Karte hinaus erweitern.

### Geplante Änderungen

#### 4.1 Import aus weiteren Quellen

- [-] Adapter für zusätzliche Quellen
  - Lokale IGC-Dateien aus Logger-Software oder anderen Plattformen importieren.
  - Optional: XContest-Profil oder XCTrack-Export als weitere Eingabe.
- [-] Einheitliches Import-Schema
  - Unabhängig von der Quelle werden Flüge in dasselbe SQLite-Schema importiert.
  - Quellenkennzeichnung pro Flug (z. B. `source = 'dhv-xc'` oder `source = 'local-igc'`).

#### 4.2 Erweiterte Visualisierung

- [?] Statischer SVG/PNG-Export der Karte für Berichte oder Druck.
- [?] Heatmap der häufigsten Start-/Landeorte.
- [?] 3D-Ansicht der Tracks (potenziell eigenes Minor-Release, wenn umfangreicher).

### Motivation

Mit mehreren Datenquellen wächst der lokale Flugbestand; gleichzeitig soll die räumliche Aufbereitung
über die interaktive Basiskarte aus v0.3.0 hinaus erweitert werden.

### Technische Hinweise

- Kein eigenes Web-Backend: Kartenexport weiterhin als statische HTML-Datei unter `data/export/`.
- Adapter-Struktur einführen: `scripts/sources/base.py`, `scripts/sources/dhv_xc.py`, `scripts/sources/local_igc.py`.
- 3D erfordert ADR und ggf. neue Abhängigkeiten (z. B. Cesium / deck.gl / matplotlib 3D).

---

## v0.5.0 — Deduplizierung & Konsistenzprüfung

**Ziel:** Bei mehreren Quellen und wiederholten Importen sicherstellen, dass jeder Flug nur einmal im Bestand existiert und die Daten konsistent sind.

### Geplante Änderungen

- [-] Deduplizierung über Quellen hinweg
  - Dedup-Schlüssel aus Flugdatum, Startplatz, Flugdauer und Logger-Seriennummer (A-Record).
  - Zusammenführen mehrerer IGC-Dateien für denselben Flug, falls unterschiedliche Quellen denselben Flug liefern.
- [-] Konsistenzprüfung
  - Prüfung, ob Flugmetadaten und IGC-Dateien zueinander passen.
  - Erkennung von Lücken (z. B. fehlende IGC-Dateien für einen importierten Flug).
  - Erkennung von Dubletten in `data/igc/`.
- [-] Reconciliation-Report
  - HTML/JSON-Report, der Dubletten, Lücken und Konsistenzprobleme auflistet.

### Motivation

Sobald mehrere Quellen und regelmäßige Importe hinzukommen, entstehen schnell Dubletten und Inkonsistenzen.
v0.5.0 soll den lokalen Flugbestand zuverlässig aufräumen und dem Nutzer transparent melden, was zusammengeführt oder nachgeholt werden muss.

### Technische Hinweise

- Dedup-Logik als separater Schritt `scripts/deduplicate_flights.py`, der die SQLite-DB analysiert.
- Keine automatische Löschung von IGC-Dateien ohne Bestätigung/Backup-Option.
- ADR erforderlich: Strategie für Konfliktauflösung (welche Quelle gewinnt bei widersprüchlichen Metadaten?).

---

## Nicht geplant / Zurückgestellt

- Cloud-Hosting oder zentrale Web-API (Projekt bleibt lokal-first).
- Kryptographische G-Record-Verifikation (außerhalb des Projekt-Scope; strukturelle Validierung bleibt ausreichend).
- Echtzeit-Tracking oder Live-Upload von Flügen.
- Höhenflug-Nachweis als dediziertes Feature (optional; siehe [Unreleased] / Optional).

---

## Referenzen

- [`docs/TODO.md`](./TODO.md) — Lebendige Aufgabenliste
- [`CHANGELOG.md`](../CHANGELOG.md) — Versionshistorie
- [`docs/decisions/ADR-001-architecture-techstack.md`](./decisions/ADR-001-architecture-techstack.md) — Architekturentscheidungen

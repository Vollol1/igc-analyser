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

## [Unreleased] / Nächstes Release

Dieser Abschnitt sammelt Änderungen, die noch keinem Release zugeordnet sind, aber bereits fest eingeplant oder in Arbeit.

- Testsuite aufbauen (`tests/`)
  - Unit-Tests für IGC-Validierung, Dateinamensgenerierung, Hash-Bildung.
  - Integrationstest mit lokalen Mock-IGC-Dateien ohne Netzwerk.
  - CI-Grundgerüst für wiederkehrende Testläufe.
- Resume-Logik für fehlgeschlagene Downloads verbessern
  - `attempts`-Zähler in der Downloader-State-DB (`data/igc_extractor.db`).
  - Erkennung dauerhaft fehlgeschlagener Flüge, statt endloser Wiederholung.
- SQLite-Datenbanken konsolidieren (Vorbereitung)
  - Dokumentieren, warum es aktuell zwei Datenbanken gibt (`igc_extractor.db` vs. `igc-extractor.db`).
  - ADR erarbeiten, der den Migrationspfad zu einer einzigen DB beschreibt.
- `LandingLocation` aus der DHV-XC Detailseite scrapen und im Export berücksichtigen.
- Validierungs- und Ausreißer-Checks für Flugdaten (Distanz, Flugzeit, Höhenmeter).

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

## v0.3.0 — IGC-Export für Höhenflug-Nachweis

**Ziel:** Aus den lokalen Flugdaten einen Nachweis für Höhenflüge generieren, der für Vereins-/Lizenz-Zwecke verwendet werden kann.

### Geplante Änderungen

- [-] Export-Modul für Höhenflugnachweise
  - Filter nach Datum, Startplatz, Gleitschirm und Mindest-Höhe.
  - Strukturierter CSV- oder PDF-Export mit Flugnummer, Datum, Start-/Landeplatz, Dauer und Best-Distanz.
- [-] Erweiterte SQLite-Views
  - View `v_hoehenflug_nachweis` mit den für den Nachweis relevanten Feldern.

### Motivation

Viele Vereine und Lizenzen verlangen einen schlüssigen Höhenflug-Nachweis.
Statt manuell aus dhv-xc.de zu kopieren, soll igc-extractor einen reproduzierbaren, lokalen Export erzeugen.

### Technische Hinweise

- Reine Text/CSV-Generierung zuerst; PDF-Ausgabe optional über `reportlab` oder WeasyPrint.
- Keine kryptographische G-Record-Prüfung (weiterhin nur strukturelle Validierung).
- Export-Dateien landen unter `data/export/`.

---

## v0.4.0 — Kartenvisualisierung & Import aus weiteren Quellen

**Ziel:** Flüge nicht nur als Datensatz, sondern auch visuell erfahrbar machen und weitere Datenquellen anbinden.

### Geplante Änderungen

#### 4.1 Kartenvisualisierung

- [-] Kartenexport der importierten Flüge
  - Statische Karte (z. B. mit `folium` oder `leaflet`-basiertem HTML-Export), die Startplätze oder Flugtrajektorien zeigt.
  - Optional: Heatmap der häufigsten Start-/Landeorte.
- [-] Trajektorien parsen
  - B-Records aus IGC-Dateien auslesen (Breite, Länge, Höhe).
  - Vereinfachte Darstellung, keine Echtzeit-Wiedergabe.

#### 4.2 Import aus weiteren Quellen

- [-] Adapter für zusätzliche Quellen
  - Lokale IGC-Dateien aus Logger-Software oder anderen Plattformen importieren.
  - Optional: XContest-Profil oder XCTrack-Export als weitere Eingabe.
- [-] Einheitliches Import-Schema
  - Unabhängig von der Quelle werden Flüge in dasselbe SQLite-Schema importiert.
  - Quellenkennzeichnung pro Flug (z. B. `source = 'dhv-xc'` oder `source = 'local-igc'`).

### Motivation

Die rein tabellarische Aufbereitung reicht für Analysen, nicht aber für räumliches Verständnis.
Eine Kartenvisualisierung macht Startplatz-Cluster und Fluggebiete sofort sichtbar.
Gleichzeitig sollen Flüge aus anderen Quellen in denselben lokalen Bestand einfließen.

### Technische Hinweise

- Kein eigenes Web-Backend: Kartenexport als statische HTML-Datei unter `data/export/`.
- Für B-Record-Parsing können existierende Bibliotheken oder eine schlanke Eigenlösung evaluiert werden (ADR erforderlich).
- Adapter-Struktur einführen: `scripts/sources/base.py`, `scripts/sources/dhv_xc.py`, `scripts/sources/local_igc.py`.

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

---

## Referenzen

- [`docs/TODO.md`](./TODO.md) — Lebendige Aufgabenliste
- [`CHANGELOG.md`](../CHANGELOG.md) — Versionshistorie
- [`docs/decisions/ADR-001-architecture-techstack.md`](./decisions/ADR-001-architecture-techstack.md) — Architekturentscheidungen

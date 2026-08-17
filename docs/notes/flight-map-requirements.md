# Anforderungen: Interaktive IGC-Flugkarte

Dieses Dokument sammelt die Anforderungen für das neue Kartenfeature von igc-extractor.

---

## Ziel

Eine **lokale, interaktive Karte aller heruntergeladenen IGC-Flüge** als eigenständige HTML-Datei erzeugen.
Die Karte kann direkt im Browser geöffnet werden und zeigt Flugtrajektorien, Startplätze sowie begleitende
Statistiken ohne Netzwerk-Backend oder externe Datenbankanbindung.

## Nicht-Ziele

Folgende Dinge gehören **nicht** zur Basisversion des Features:

- Ein eigenes Web-Backend oder ein online geteiltes Dashboard.
- 3D-Darstellung von Tracks oder Gelände in der Basisversion.
- Cloud-Hosting, Echtzeit-Tracking oder Live-Upload von Flügen.

## Basisfunktionen

### Neues Skript

- `scripts/export_flight_map.py` wird neu erstellt.
- Es liest `data/processed/flights.jsonl` und die zugehörigen IGC-Dateien in `data/igc/`.
- Es parst B-Records (Lat/Lon/Höhe) aus den IGC-Dateien.
- Es erzeugt eine Leaflet-basierte HTML-Karte mit OpenStreetMap-Hintergrund.

### Karteninhalte

- **Tracks als Polylinien**: Jeder Flug wird als farbige Polylinie über seine B-Record-Punkte dargestellt.
- **Startplatz-Marker**: Für jeden erkannten Startplatz wird ein Marker gesetzt.
- **Interaktive Popups**: Klick auf Track oder Marker zeigt Flugdetails (z. B. Flugdatum, Startplatz, Gleitschirm, Flugzeit, XC-Distanz, Validierungsstatus).
- **Statistik-Panel**: Übersichts-Panel mit mindestens:
  - Anzahl der dargestellten Flüge
  - Zeitraum (frühester/spätester Flug)
  - Gesamtflugzeit (Stunden/Minuten)
  - Summe XC-Distanz in km
  - Bester Flug (z. B. nach Distanz oder Punkten)
  - Anzahl Startplätze
  - Anzahl unterschiedlicher Gleitschirme
  - Anzahl valid / invalid / missing IGC-Dateien

### Gruppierungen / Layer (umschaltbar)

Die Karte erhält umschaltbare Layer-Gruppen:

- **Kategorie** (Default): Lokal / XC / Höhenflug
- **Startplatz**: Flüge nach Startplatz gruppieren
- **Flugjahr**: Flüge nach Jahr gruppieren
- **Gleitschirm**: Flüge nach Gleitschirm gruppieren

Beim Start ist die Kategorie-Layer aktiv; weitere Layer können vom Nutzer ein- und ausgeschaltet werden.

## Output-Dateien

Ein Lauf von `scripts/export_flight_map.py` schreibt:

- `data/export/flights_map_<run_id>.html` – die interaktive Karte
- `data/logs/export_flight_map_<run_id>.log` – detailliertes Log
- `data/logs/export_flight_map_summary_<run_id>.json` – Zusammenfassung der Kartenstatistik

`<run_id>` folgt dem bestehenden Zeitstempel-Schema der anderen Export-Skripte.

## Technische Rahmenbedingungen

- **Kartenbibliothek**: [Leaflet](https://leafletjs.com/) + OpenStreetMap-Tiles.
- **Generierung**: Reine Python-Generierung des HTML/JS/CSS; keine serverseitige Laufzeit nötig.
- **Parser**: B-Record-Parser soll wiederverwendbar sein, damit er auch für zukünftige Features genutzt werden kann.
- **3D**: 3D-Darstellung (z. B. mit CesiumJS oder WebGL-basierten Bibliotheken) wird vorgemerkt und in einer späteren Iteration behandelt.

## Iterationsideen (ohne fixe Versionsnummern)

Die folgenden Schritte sind als offene Iterationskette gedacht:

1. **Basis-Karte**: Einzelner Kategorie-Layer (Lokal / XC / Höhenflug) mit Tracks, Startplatz-Markern und Popups.
2. **Zusätzliche Gruppierungen**: Startplatz-, Flugjahr- und Gleitschirm-Layer ergänzen.
3. **Statischer Export**: SVG/PNG-Export der Karte für Berichte oder Druck.
4. **Spätere 3D-Ansicht**: Tracks und Höhenprofil in einer 3D-Ansicht darstellen; bei Umsetzung potenziell ein eigenes Minor-Release.

Die genauen Versionsnummern werden bei der Release-Planung festgelegt.

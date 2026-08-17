# IGC-Download- & Import-Pipeline Notes

Lebendiges Notizbuch für Erkenntnisse, Probleme und offene Fragen rund um den Download von IGC-Dateien von dhv-xc.de und deren lokale Verarbeitung.

---

## Login-Mechanismus

`scripts/list_flights.py` und `scripts/download_igc.py` melden sich bei dhv-xc.de an. Beide nutzen den gemeinsamen `DhvXcClient` in `scripts/dhv_xc_client.py`.

- **CSRF-Token**: Die Login-Seite liefert `jc.token = '<32-char-hex>'` im HTML-Head. Der Client sendet es als Header `X-Csrf-Token`.
- **Login-Endpoint**: `POST /api/xc/login/login` mit `uid`, `pwd`, `stay=1`, `dhvfetch=0`.
- **Session-Cookie**: `PHPSESSID`. Der Server setzt es nach erfolgreichem Login.
- **IGC-Download-Endpoint**: `GET /flight/{IDFlight}/igc`, ausgeführt über dieselbe authentifizierte Session.
- **DHV service portal**: Falls das Konto über den DHV-Service-Portal-Flow verknüpft werden muss (`FAILURE_DHVMAPPING_REQUIRED`), ist derzeit nur ein manueller Browser-Login als Workaround möglich.

### Beobachtungen / Risiken

- [ ] Wie lange bleibt `PHPSESSID` gültig? Muss der Login pro Lauf erneuert werden?
- [ ] Verändert dhv-xc.de die Position von `jc.token` oder den Header-Namen?
- [ ] Tritt bei wiederholtem Login ein Rate-Limit ein?

---

## Rate-Limiting

| Aspekt | Beobachtung |
|--------|-------------|
| Login | Bisher kein hartes Rate-Limit beobachtet, aber Anmeldeversuche sollten nicht in schneller Schleife erfolgen. |
| Flugliste | Pagination via `navpars={"start":0,"limit":50,...}`. Seiten sollten seriell abgerufen werden. |
| IGC-Download | Pro Flug ein GET auf `/flight/{IDFlight}/igc`. Bei schneller serieller Abfolge (z. B. 1 s Rate-Limit) hängen Downloads nach ~50–60 Flügen ohne erkennbaren HTTP-Fehler. Vermutung: Serverseitige Soft-Limit / Session-Ablauf bei langer Download-Phase. |
| allgemein | 429/503-Responses noch nicht beobachtet. Bei Auftreten Retry mit exponentiellem Backoff ergänzen. |

### Empfohlene Höflichkeitsregeln

1. Maximal eine Anfrage pro Sekunde bei der Flugliste.
2. IGC-Downloads seriell oder mit sehr geringer Parallelität.
3. Downloads in Batches durchführen (z. B. 40 Flüge) und zwischen den Batches frisch anmelden sowie 15–30 s pausieren.
4. Keine scraping-artigen Endlos-Loops ohne `--resume`/`--limit`.

### Real beobachtete Download-Zeiten (29.07.2026)

- ~288 eigene Flüge, davon 240 tatsächlich herunterzuladen.
- Mit `--rate-limit 2.0` und `--batch-size 40 --batch-pause 30` ca. 10–12 Minuten Gesamtlaufzeit inklusive Pausen.
- Durchschnittliche Download-Zeit pro Flug: 0,5–2 s; gelegentliche größere Dateien (Langstreckenflüge) bis ~5 s.
- Keine HTTP-429/503-Fehler, aber einzelne Hänger bei Langzeit-Sessions ohne Batch-Pause.

---

## Resume / Idempotenz

Die Pipeline ist so konzipiert, dass unterbrochene Läufe fortgesetzt werden können.

- `scripts/igc_extractor.py --resume` überspringt bereits vorhandene `.igc`-Dateien in `data/igc/`.
- `data/igc_extractor.db` speichert pro Flug Status (`downloaded`, `failed`, `missing`) für den Downloader.
- `data/igc-extractor.db` ist das Ziel von `import_flights.py` mit Flugmetadaten, Hashes und Validierungsstatus.
- Langfristig sollen die beiden Datenbanken konsolidiert werden (siehe `docs/ROADMAP.md` v0.2.0).
- `data/processed/flights.jsonl` wird bei jedem `list_flights.py`-Lauf idempotent neu geschrieben.

### Offene Fragen

- [ ] Soll das SQLite-State-Schema um einen `attempts`-Zähler erweitert werden, um dauerhaft fehlgeschlagene Flüge zu erkennen?
- [ ] Wie wird mit Flügen umgegangen, die auf dem Server gelöscht wurden, aber lokal noch vorhanden sind?

---

## Validierung

`scripts/import_flights.py` führt eine strukturelle Minimalvalidierung durch:

- A-Record am Dateianfang.
- Mindestens ein B-Record.
- G-Record am Dateiende.
- Lesbarer UTF-8-Text, Mindestgröße 50 Byte.

### Bekannte Einschränkungen

- Die kryptographische G-Record-Signatur wird **nicht** geprüft.
- Beschädigte Dateien, die trotzdem diese Minimalstruktur erfüllen, werden als `valid` markiert.
- IGC-Dateien von verschiedenen Logger-Herstellern können leicht unterschiedliche A-Record-Formate haben.

### Offene Fragen

- [ ] Soll die Validierung auch auf obligatorische C-Record-Task-Deklarationen prüfen?
- [ ] Sollen Checksum / Security-Records (G-Record) in Zukunft verifiziert werden?
- [ ] Wie wird mit IGC-Dateien umgegangen, die keine G-Record-Zeile haben (ältere Logger)?

---

## Datenbank-Incident (2026-08-17): `flights`/`flight_stats` in `data/igc_extractor.db`

### Was passiert ist

- Ein Lauf von `scripts/igc_extractor.py` hat an `scripts/import_flights.py` versehentlich `--db data/igc_extractor.db` übergeben, statt des vorgesehenen Analyse-DB-Pfades `data/igc-extractor.db`.
- Dadurch wurden die Importtabellen `flights` und `flight_stats` in der eigentlichen Downloader-State-DB angelegt.
- Zustand vor der Bereinigung:
  - `data/igc_extractor.db` enthielt `flights` (306 Zeilen: 199 valid, 107 invalid) und `flight_stats` (2 Zeilen).
  - `data/igc-extractor.db` enthielt bereits `flights` (288 Zeilen: 287 valid, 1 invalid) und `flight_stats` (1 Zeile).

### Analyse

- 288 Flug-IDs waren in beiden Datenbanken vorhanden.
- Die 18 zusätzlichen IDs in `data/igc_extractor.db` waren allesamt als `valid` markiert und in `data/processed/flights.jsonl` vorhanden, hatten aber aus einem früheren Lauf keine Einträge in der Analyse-DB.
- Für die 288 gemeinsamen IDs wies `data/igc_extractor.db` 106 als `invalid` aus, während `data/igc-extractor.db` sie als `valid` kennzeichnete (mit korrektem Hash). Der Grund war ein früheres Import-Skript, das G-Records zu streng geprüft hat; die Analyse-DB enthält den aktuellen, korrekten Status.
- `flight_stats` der State-DB war ein Duplikat/Verwässerung der Analyse-Stats.

### Entscheidung

- Die Tabellen in `data/igc_extractor.db` konnten **nicht** einfach gedroppt werden, ohne Daten zu verlieren, weil 18 vollständige, validierte Flugzeilen ausschließlich dort standen.
- **Migrationsstrategie**: Nur die 18 Analyse-DB-fremden Flugzeilen sowie die dort fehlende `flight_stats`-Zeile (`run_id=20260817_162404`) wurden in `data/igc-extractor.db` übertragen (`INSERT ... ON CONFLICT(IDFlight) DO UPDATE`). Konflikte bei den 288 gemeinsamen IDs wurden zugunsten der bereits korrekten Analyse-DB aufgelöst.
- Anschließend wurden die importierten Tabellen `flights` und `flight_stats` aus `data/igc_extractor.db` entfernt (`DROP TABLE`), damit die State-DB wieder für ihren vorgesehenen Zweck (Downloader-Resume/Idempotenz) frei ist.

### Durchgeführte Bereinigung

1. 18 ausschließlich in `data/igc_extractor.db` vorhandene Flugzeilen nach `data/igc-extractor.db` migriert.
2. Fehlende `flight_stats`-Zeile `20260817_162404` nach `data/igc-extractor.db` migriert.
3. `DROP TABLE flights` und `DROP TABLE flight_stats` in `data/igc_extractor.db` ausgeführt.
4. `PRAGMA integrity_check` auf `data/igc-extractor.db` erfolgreich ausgeführt.

### Zustand nach der Bereinigung

- `data/igc_extractor.db`: enthält nur noch `sqlite_sequence`, keine `flights`-Tabelle mehr.
- `data/igc-extractor.db`: 306 Flugzeilen (305 valid, 1 invalid), vollständige `flight_stats`.
- Keine IGC-Dateien gelöscht; Analyse-DB unversehrt.
- Der Fehler, der den falschen DB-Pfad verursacht hat, wurde bereits in `scripts/igc_extractor.py` korrigiert (siehe CHANGELOG.md `[Unreleased]`).

---

## Kartenfeature (ab geplant v0.3.0)

- Neuer Export-Schritt `scripts/export_flight_map.py` wird die IGC-Tracks in eine interaktive Leaflet-HTML-Karte überführen.
- Input: `data/processed/flights.jsonl` + IGC-Dateien in `data/igc/`.
- Output: `data/export/flights_map_<run_id>.html`, `data/logs/export_flight_map_<run_id>.log`, `data/logs/export_flight_map_summary_<run_id>.json`.
- B-Record-Parser soll wiederverwendbar sein, damit er auch für zukünftige 3D-Visualisierungen genutzt werden kann.
- Details siehe [`flight-map-requirements.md`](./flight-map-requirements.md).

## Changelog

- **2026-08-17**: Datenbank-Incident bereinigt: `flights`/`flight_stats` aus `data/igc_extractor.db` entfernt und fehlende Daten nach `data/igc-extractor.db` migriert.
- **2026-08-17**: Anforderungen für interaktive IGC-Flugkarte dokumentiert (`flight-map-requirements.md`); v0.3.0 in `docs/ROADMAP.md` auf Kartenfeature umgestellt.
- **2026-07-29**: Echter End-to-End-Lauf mit 288 eigenen Flügen durchgeführt.
  - Download-Strategie: `--rate-limit 2.0 --batch-size 40 --batch-pause 30`.
  - Ergebnis: 288/288 IGC-Dateien heruntergeladen, 287/288 valid, 1 invalid (Flug 2234459 ohne G-Record).
  - Validierung korrigiert: G-Record muss nach dem letzten B-Record liegen, nicht unbedingt als letzte Zeile der Datei (Naviter-Logger hängen `LX*` Endinfo-Datensätze nach dem G-Record an).
- **2026-07-26**: Datei angelegt. Enthält Platzhalter für zukünftige Beobachtungen zu Login, Rate-Limiting, Resume und Validierung.

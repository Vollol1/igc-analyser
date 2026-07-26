# IGC-Download- & Import-Pipeline Notes

Lebendiges Notizbuch für Erkenntnisse, Probleme und offene Fragen rund um den Download von IGC-Dateien von dhv-xc.de und deren lokale Verarbeitung.

---

## Login-Mechanismus

`scripts/list_flights.py` und `scripts/igc_extractor.py` melden sich bei dhv-xc.de an.

- **CSRF-Token**: Die Login-Seite liefert `jc.token = '<32-char-hex>'` im HTML-Head. Der Client sendet es als Header `X-Csrf-Token`.
- **Login-Endpoint**: `POST /api/xc/login/login` mit `uid`, `pwd`, `stay=1`, `dhvfetch=0`.
- **Session-Cookie**: `PHPSESSID`. Der Server setzt es nach erfolgreichem Login.
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
| IGC-Download | Pro Flug ein GET auf `/flight/{IDFlight}/igc`. Keine parallelen Downloads ohne explizite Freigabe implementiert. |
| allgemein | 429/503-Responses noch nicht beobachtet. Bei Auftreten Retry mit exponentiellem Backoff ergänzen. |

### Empfohlene Höflichkeitsregeln

1. Maximal eine Anfrage pro Sekunde bei der Flugliste.
2. IGC-Downloads seriell oder mit sehr geringer Parallelität.
3. Keine scraping-artigen Endlos-Loops ohne `--resume`/`--limit`.

---

## Resume / Idempotenz

Die Pipeline ist so konzipiert, dass unterbrochene Läufe fortgesetzt werden können.

- `scripts/igc_extractor.py --resume` überspringt bereits vorhandene `.igc`-Dateien in `data/igc/`.
- `data/igc_extractor.db` speichert pro Flug Status (`downloaded`, `failed`, `missing`).
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

## Changelog

- **2026-07-26**: Datei angelegt. Enthält Platzhalter für zukünftige Beobachtungen zu Login, Rate-Limiting, Resume und Validierung.

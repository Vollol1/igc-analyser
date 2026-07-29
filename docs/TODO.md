# igc-extractor TODO

Lebendige Aufgabenliste für den igc-extractor. Diese Datei liegt im Repository, damit sie über Kanban-Resets und Agent-Session-Neustarts hinweg erhalten bleibt.

## Status-Legende

- `[ ]` offen
- `[-]` in Arbeit
- `[x]` erledigt
- `[?]` optional / zurückgestellt
- `[!]` blockiert

## Aktuell in Arbeit

_(keine)_

## Kurzfristig geplant

- [x] Login-Mechanismus dokumentieren und robust gegen Token-/Layout-Änderungen machen
- [x] Rate-Limiting / Retry-Logik für Downloads ergänzen
- [x] IGC-Validierung erweitern (G-Record-Signatur optional, C-Record-Checks)
  - G-Record-Check korrigiert: Er muss nach dem letzten B-Record liegen, nicht zwingend als letzte Zeile der Datei.
- [ ] Resume-Logik für fehlgeschlagene Downloads verbessern (`attempts`-Zähler in DB)

## Erledigt

- [x] `scripts/download_igc.py` repariert
  - Liest jetzt das JSONL-Schema von `list_flights.py` (`IDFlight`, `FlightDate`, `TakeoffLocation`, `IgcUrl`).
  - Verwendet den gemeinsamen `DhvXcClient` (`scripts/dhv_xc_client.py`) mit Session-/CSRF-/PHPSESSID-Login statt HTTP-Basic-Auth.
  - Rate-Limiting (`--rate-limit`) und Retry-Logik (`--max-retries`) bleiben erhalten.
  - Unterstützt jetzt `--offset` und `--limit` für stückweise/batchweise Downloads.
  - Logs/Summaries werden weiterhin nach `data/logs/` geschrieben.
- [x] Gemeinsames `scripts/dhv_xc_client.py` aus `list_flights.py` extrahiert
  - Zentraler authentifizierter Client für Login, Flugliste und IGC-Download.
- [x] `scripts/igc_extractor.py` erweitert
  - `--rate-limit`, `--max-retries`, `--batch-size`, `--batch-pause` werden an `download_igc.py` weitergegeben.
  - Download läuft intern in Batches mit Re-Login und Pause zwischen den Batches.
- [x] Login-Mechanismus dokumentieren und robust gegen Token-/Layout-Änderungen machen
- [x] Rate-Limiting / Retry-Logik für Downloads ergänzen
- [x] Dokumentations- und Agent-Verhaltens-Struktur aus gag-atlas übernommen
  - `AGENT_BEHAVIOR_NOTES.md` im Repo-Root erstellt.
  - `docs/notes/kanban-notes.md` mit Workflow-Beobachtungen erstellt.
  - `docs/notes/pipeline-notes.md` für zukünftige IGC-Download/Import-Beobachtungen erstellt.
  - `docs/runbooks/download-igc.md` mit Schritt-für-Schritt-Anleitung erstellt.
  - `docs/decisions/ADR-001-architecture-techstack.md` auf neues docs-Schema aktualisiert.
  - `README.md` verlinkt `AGENT_BEHAVIOR_NOTES.md` und die wichtigsten docs/-Unterverzeichnisse.
- [x] Vollständige Pipeline aus Flugliste → Download → Import → Export automatisiert testen
  - Echter End-to-End-Lauf am 29.07.2026 mit 288 eigenen Flügen: 288/288 IGC-Dateien heruntergeladen, 287/288 valid, 1 invalid (Flug 2234459 ohne G-Record).

## Mittelfristig geplant

- [x] Datenqualität der importierten Flüge über Stichproben evaluieren
  - Stichprobe zeigt: Naviter-Logger hängen `LX*` Endinfo-Datensätze nach dem G-Record an; daher wurde die Validierung angepasst.
- [ ] Datenqualität weiterhin gelegentlich prüfen (z. B. nach jedem größeren Download).

## Abgeschlossen

_(keine außerhalb von "Erledigt")_

## Optional / Zurückgestellt

- [?] Web-Frontend oder Visualisierung für heruntergeladene Flüge
- [?] Cloud-Fallback für dhv-xc.de (aktuell nicht vorgesehen)

## Langfristig / Vision

- [ ] IGC-Download- und Import-Pipeline vollständig ohne manuelle Worktree-Intervention ausführbar
- [ ] Alle gewünschten Flüge lokal vorhanden, validiert und in SQLite importiert

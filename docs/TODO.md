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

- [ ] Login-Mechanismus dokumentieren und robust gegen Token-/Layout-Änderungen machen
- [ ] Rate-Limiting / Retry-Logik für Downloads ergänzen
- [ ] IGC-Validierung erweitern (G-Record-Signatur optional, C-Record-Checks)
- [ ] Resume-Logik für fehlgeschlagene Downloads verbessern (`attempts`-Zähler in DB)

## Erledigt

- [x] Dokumentations- und Agent-Verhaltens-Struktur aus gag-atlas übernommen
  - `AGENT_BEHAVIOR_NOTES.md` im Repo-Root erstellt.
  - `docs/notes/kanban-notes.md` mit Workflow-Beobachtungen erstellt.
  - `docs/notes/pipeline-notes.md` für zukünftige IGC-Download/Import-Beobachtungen erstellt.
  - `docs/runbooks/download-igc.md` mit Schritt-für-Schritt-Anleitung erstellt.
  - `docs/decisions/ADR-001-architecture-techstack.md` auf neues docs-Schema aktualisiert.
  - `README.md` verlinkt `AGENT_BEHAVIOR_NOTES.md` und die wichtigsten docs/-Unterverzeichnisse.

## Mittelfristig geplant

- [ ] Vollständige Pipeline aus Flugliste → Download → Import → Export automatisiert testen
- [ ] Datenqualität der importierten Flüge über Stichproben evaluieren

## Abgeschlossen

_(keine außerhalb von "Erledigt")_

## Optional / Zurückgestellt

- [?] Web-Frontend oder Visualisierung für heruntergeladene Flüge
- [?] Cloud-Fallback für dhv-xc.de (aktuell nicht vorgesehen)

## Langfristig / Vision

- [ ] IGC-Download- und Import-Pipeline vollständig ohne manuelle Worktree-Intervention ausführbar
- [ ] Alle gewünschten Flüge lokal vorhanden, validiert und in SQLite importiert

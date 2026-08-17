# Worktree-Loss-Vorfall — 2026-08-17

## Betroffener Task

- **Task-ID:** `e6fb8`
- **Titel:** Implementierung der interaktiven Karte
- **Datum des Vorfalls:** 17.08.2026

## Verlauf

1. Der Task `e6fb8` wurde im Worktree bearbeitet.
2. Dabei wurden neue bzw. geänderte Dateien erstellt:
   - `scripts/export_flight_map.py` (neu)
   - verbesserte `scripts/common.py` (geändert)
3. Der Kanban-Sidebar-Agent rief `task done` auf, bevor der Auto-Review/Merge abgeschlossen war.
4. Der Worktree wurde gelöscht.
5. Die oben genannten Dateien landeten **nicht** im Haupt-Repository (`main`).

## Ursache

- `task done` wurde ausgelöst, während die Änderungen noch uncommitted im Worktree vorlagen.
- Der Auto-Review/Merge-Prozess war zu diesem Zeitpunkt nicht erfolgreich abgeschlossen.
- Beim Löschen des Worktrees gingen die uncommitted Änderungen unwiderruflich verloren.

## Betroffene Dateien

- `scripts/export_flight_map.py` — neu erstellt, vollständig verloren.
- `scripts/common.py` — verbesserte Version verloren; `main` enthält nur den alten Stand.

## Konsequenzen

- Die Implementierung der interaktiven Karte muss wiederholt werden.
- Ein neuer Task wird im Kanban angelegt, um die Arbeit nachzuholen.
- Prozessregel wurde angepasst, um künftige Worktree-Verluste zu verhindern (siehe AGENT_BEHAVIOR_NOTES.md Regel 13).

## Gegenmassnahmen / Prozessänderungen

Siehe [AGENT_BEHAVIOR_NOTES.md](../../AGENT_BEHAVIOR_NOTES.md), Regel 13:

> `task done` darf nur nach physischem Nachweis in `main` aufgerufen werden.

Der Sidebar-Agent muss vor `task done` prüfen, dass neue Dateien und Änderungen tatsächlich in `main` vorhanden sind (`git log`, `git status`, `git diff`).

## Status

- Vorfall dokumentiert.
- Neuer Task zum Re-Implementieren der interaktiven Karte wird angelegt.

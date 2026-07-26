# Kanban-Workflow-Notizen

Notizen zum Umgang mit Tasks, Auto-Review und Worktree-Ergebnissen im igc-extractor-Kanban-Workflow.

---

## 2026-07-26 – Worktree-Ergebnisse gingen verloren, weil Auto-Review nicht aktiviert war

### Beobachtung

Bei einem Dokumentations-Task im igc-extractor-Worktree wurden mehrere neue Dateien (unter anderem in `docs/notes/` und `docs/runbooks/`) erstellt. Der Task wurde mit `task done` abgeschlossen, aber die neuen Dateien landeten nicht im Haupt-Repository. Stattdessen wurde der Worktree bereinigt, bevor der Merge stattfinden konnte.

Ursache: `--auto-review-enabled true --auto-review-mode commit` wurde nicht gesetzt. Ohne dieses Flag löscht `task done` den Worktree **vor** dem Commit/Merge, wodurch neu erstellte Dateien verloren gehen.

### Lösung

Fertige Worktree-Ergebnisse müssen ins Haupt-Repository übernommen werden, bevor der Worktree entfernt wird. Mögliche Wege:

1. **Auto-Review beim Task-Start aktivieren** (bevorzugt):
   ```bash
   # Beispiel für einen datei-erstellenden Task
   task create "Doku-Struktur übernehmen" \
     --auto-review-enabled true \
     --auto-review-mode commit
   ```
   - Das schreibt die Änderungen direkt ins Haupt-Repo, bevor der Worktree aufgeräumt wird.
   - Gilt insbesondere für neue Skripte, Configs, Docs, Testdateien und generierte Assets.

2. **Git cherry-pick aus dem Worktree** (Fallback):
   ```bash
   # Im Haupt-Repository
   cd /home/florian/git.vollol.com/fknab/igc-extractor
   git fetch origin
   git cherry-pick <worktree-commit>
   ```
   - Voraussetzung: Der Agent hat seine Änderungen im Worktree committed.
   - Bei Konflikten manuell auflösen und Commit-Message beibehalten.

3. **Kanban-Checkpoint-Refs verwenden** (wenn verfügbar):
   - Die Kanban-Umgebung speichert Checkpoints unter `.git/refs/kanban/checkpoints/`.
   - Letzten Checkpoint-Commit ermitteln und cherry-picken oder direkt mergen.

4. **Sidebar-Agent als Sicherheitsnetz**:
   - Wenn der Auto-Review/Merge-Prozess fehlschlägt, darf der Kanban-Sidebar-Agent fertige Worktree-Ergebnisse ins Haupt-Repository kopieren und committen.
   - Siehe `AGENT_BEHAVIOR_NOTES.md` Regel 8.

### Empfohlene Maßnahmen

1. **Bei jedem Task, der neue Dateien erzeugt, Auto-Review aktivieren.**
2. **Vor `task done` prüfen**, ob `task show` oder der Worktree-Status wirklich Merged/Committed anzeigt.
3. **Regelmäßige Checkpoints**: Während längerer Tasks kleine Commits im Worktree machen, um cherry-pick-fähige Zwischenstände zu haben.
4. **Nie uncommittede neue Dateien im Worktree zurücklassen**, wenn der Task beendet wird.
5. **AGENT_BEHAVIOR_NOTES.md pflegen**: Wenn das Problem erneut auftritt, diese Notiz erweitern und ggf. eine neue Regel hinzufügen.

### Offene Fragen

- [ ] Gibt es ein Kanban-Log oder einen Befehl, der anzeigt, warum ein Auto-Commit fehlgeschlagen ist?
- [ ] Lässt sich `--auto-review-mode commit` standardmäßig für alle datei-erstellenden Tasks aktivieren?
- [ ] Soll für reine Doku-Tasks grundsätzlich der Sidebar-Agent das Merge übernehmen?

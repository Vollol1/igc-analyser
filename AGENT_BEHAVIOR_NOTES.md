# ⚠️ AGENT BEHAVIOR NOTES — MANDATORY READ BEFORE EVERY SESSION

> **Permanent instructions for every coding agent working on igc-extractor.**  
> These rules override ad-hoc habits. They live in the repository root so they cannot be missed.

---

## 1. Commit hygiene — documentation first

**a) Before every commit, review and update project documentation:**

- [ ] `docs/decisions/` — Architecture Decision Records (ADRs)
- [ ] `docs/notes/` — session notes, debug/test/batch findings
- [ ] `docs/TODO.md` — living task list

If a commit changes architecture, behavior, or fixes a non-trivial bug, at least one of the three places above must be updated together with the code.

---

## 2. Capture important technical decisions

**b) Important technical decisions are recorded as ADRs.**

- Add a new ADR in `docs/decisions/` when:
  - a new dependency is introduced,
  - a core pipeline step changes,
  - a tool/configuration choice has project-wide impact,
  - a workaround or rollback option is selected over another.
- Follow the existing ADR numbering convention in `docs/decisions/`.

---

## 3. Capture session learnings

**c) Findings from debug, test, or batch sessions are documented in `docs/notes/`.**

Examples:

- dhv-xc.de API/Login-Beobachtungen
- Rate-Limiting oder Server-Fehler
- IGC-Validationsedge-Cases
- Resume/Idempotenz-Probleme
- Credential-/Session-Handling

Keep notes concise, timestamped, and reproducible.

---

## 4. Keep `docs/TODO.md` alive

**d) After every completed task, update `docs/TODO.md`:**

- Mark done items with `[x]` and move them to **Abgeschlossen** if they were major milestones.
- Update statuses (`[ ]` offen, `[-]` in Arbeit, `[!]` blockiert).
- Add newly discovered open tasks immediately.
- Do not let the TODO drift more than one task behind reality.

---

## 5. Repository boundary — worktree only

**e) Agent code changes are made and committed only inside the worktree.**

- The active worktree is `/home/florian/.cline/worktrees/51c1d/igc-extractor`.
- Do **not** modify files in the main repository directory directly.
- Merging into the main repo happens through the Kanban workflow, never by an ad-hoc agent commit.

---

## 6. Long-running tasks must not block the agent

**f) Long-running tasks such as large IGC downloads or batch imports are delegated to local background processes, not run blocking inside the agent process.**

- Use helper scripts like `scripts/igc_extractor.py` or `scripts/import_flights.py` started by the user.
- The agent may prepare, review, or resume such tasks, but must not hold the conversation waiting for hours of network I/O.
- Prefer `--resume`, status JSON, and log files for asynchronous progress.

---

## 7. Tests must pass before commit (when tests exist)

**g) Before every commit, project tests must be green — but the project currently has no `tests/` directory yet:**

```bash
# Currently there is no tests/ folder.
# As soon as tests exist, run:
pytest tests/
```

- Run the full test suite in the project venv.
- Fix failures before committing.
- If a failing test is out of scope, explicitly state why and do not silently skip it.
- **Known TODO:** create a `tests/` suite (see `docs/TODO.md` and `docs/ROADMAP.md` v0.2.0).  
  Until then, at least run `python -m py_compile` on changed scripts and verify `--help` still works.

---

## 8. Kanban-Sidebar-Agent darf Worktree-Ergebnisse ins Haupt-Repo übernehmen

**h) Wenn der normale Auto-Review/Merge-Prozess nicht zuverlässig funktioniert, darf und soll der Kanban-Sidebar-Agent fertige Worktree-Ergebnisse ins Haupt-Repository kopieren und committen.**

- Diese Hilfestellung ist beabsichtigt und erwünscht, besonders für kleine, niedrig-risiko Tasks.
- Vorgehen:
  1. Worktree-Stand prüfen (`git status`, `git diff`, Dateien im Worktree).
  2. Geänderte/erstellte Dateien selektiv ins Haupt-Repository kopieren.
  3. Passende Commit-Messages verwenden (bestehende Convention beibehalten, Prefix berücksichtigen).
  4. Zugehörige Kanban-Tasks auf `done` setzen.
- Keine großen, riskanten Änderungen ohne Sicherheitscheck kopieren; bei Zweifeln den Nutzer informieren.

---

## 9. Auto-Review für Datei-erstellende Tasks

**i) Wenn ein Task neue Dateien erstellt, die nach Abschluss im Haupt-Repo landen sollen, MUSS `--auto-review-enabled true --auto-review-mode commit` gesetzt werden.**

- `task done` löscht den Worktree **vor** dem Merge, wodurch neu erstellte Dateien verloren gehen.
- Auto-commit verhindert das, indem die Dateien vor dem Worktree-Cleanup committed werden.
- Gilt insbesondere für: neue Skripte, Configs, Docs, Testdateien, generierte Assets.
- Bei reinen Änderungen an bestehenden Dateien (ohne neue Files) ist Auto-Review optional.

---

## 10. Wiederkehrende Muster dokumentieren

**j) Wenn ein Problem oder eine Lösung mehrfach auftritt und der Agent das erkennt, MUSS er eine neue Regel in `AGENT_BEHAVIOR_NOTES.md` vorschlagen oder direkt per Task einfügen lassen.**

- Kein implizites Wissen ansammeln – alles Explizite gehört in diese Datei.
- Der Agent soll proaktiv Patterns erkennen und bei ≥2 Vorkommnissen eine Regel formulieren.
- Neue Regeln werden mit fortlaufender Nummer und Buchstabe eingefügt.
- Die Quick Checklist wird bei jeder neuen Regel mit einem passenden Checkbox-Item ergänzt.

---

## 11. Sidebar-Agent reviewed, sichert und committet Worktree-Ergebnisse aktiv

**k) Wenn der Nutzer den Kanban-Sidebar-Agent um einen Status-Check bittet oder der aktive Task im Worktree auf `review` steht, soll der Sidebar-Agent eigenständig prüfen, ob die Ergebnisse valide und vollständig sind.**

- Checkliste für den Review:
  1. `kanban task list` aufrufen, um den aktuellen Stand zu sehen.
  2. Im Haupt-Repository `git status` / `git diff` prüfen (Worktree-Änderungen werden dorthin gemerged).
  3. Syntaktische Korrektheit prüfen: `python -m py_compile <geänderte_skripte>` und `--help` Aufrufe.
  4. Logische Korrektheit prüfen: kleine, zielgerichtete Tests oder Inspektionen, die das Task-Ziel sicherstellen (z. B. JSONL-Schema passt, Client wird korrekt verwendet).
  5. Dokumentation prüfen: `docs/TODO.md`, `docs/notes/`, `docs/runbooks/` – sind die vom Task berührten Docs konsistent?
  6. Bei Erfolg: Änderungen ins Haupt-Repository committen und den Task auf `done` setzen, damit verlinkte Folge-Tasks automatisch starten können.
  7. Bei Fehlern oder Unvollständigkeiten: den Nutzer informieren und keine unvollständigen Ergebnisse committen.
- Diese Verhaltensweise sichert ab, dass Auto-Review-Fehlschläge oder hängende Worktrees nicht die ganze Kette blockieren.
- Sie ist explizit erwünscht, wenn der Nutzer danach fragt („wie sieht's aus?“, „bitte reviewn“).

---

## 12. Relative Links in Gitea-Releases

**l) Für Release-Beschreibungen in Gitea werden ausschließlich relative Links verwendet, die auf den jeweiligen Tag verweisen.**

- Verboten: absolute URLs wie `http://localhost:30030/...`, Links auf `main` oder `blob/...`-Pfade.
- Korrektes Muster für ein Repository `/fknab/igc-extractor` und Tag `v0.2.0`:
  ```markdown
  [CHANGELOG.md](../igc-extractor/src/tag/v0.2.0/CHANGELOG.md)
  ```
- Begründung: Von der Release-URL `/fknab/igc-extractor/releases/tag/v0.2.0` führt `../igc-extractor/` zurück auf die Repository-Ebene; `src/tag/v0.2.0/CHANGELOG.md` zeigt dann auf die Datei im Tag-Source.
- Dieses Muster gilt für alle zukünftigen Releases und Dokumenten-Verweise innerhalb von Gitea-Release-Notizen.

---

## 13. `task done` nur nach physischem Nachweis in `main`

**m) Der Kanban-Sidebar-Agent darf `task done` NIE aufrufen, bevor er geprüft hat, dass alle neuen Dateien und Änderungen tatsächlich im Haupt-Repository erscheinen (`git log`, `git status`, `git diff`).**

- `task done` löscht den Worktree. Wenn die Ergebnisse nicht zuvor committed und in `main` nachweisbar sind, gehen neue Dateien und uncommitted Änderungen unwiderruflich verloren.
- Wenn `task done` den Worktree dennoch löscht und die Änderungen nicht in `main` sind, müssen die Dateien vor dem endgültigen Löschen manuell aus dem letzten Checkpoint oder Worktree-Backup ins Haupt-Repository kopiert und committet werden (siehe Regel 8).
- Für Tasks mit `--auto-review-enabled true` muss der Agent nach `task done` sofort `git log` im Haupt-Repository prüfen. Fehlen die erwarteten Ergebnisse, muss er die Dateien aus dem letzten Checkpoint/Worktree-Backup ins Haupt-Repo übernehmen und einen Nachfolge-Commit durchführen.
- Der physische Nachweis in `main` ist die einzige akzeptable Bedingung, um `task done` auszulösen.

---

## 14. Sidebar-Agent darf Dokumentation direkt pflegen — aber committen und konfliktfrei

**n) Der Kanban-Sidebar-Agent darf und soll Notizen, Runbooks, TODOs und andere rein dokumentarische Dateien eigenständig bearbeiten, ohne dafür einen separaten Kanban-Task anzulegen.**

- Betroffen sind z. B. `docs/notes/`, `docs/runbooks/`, `docs/TODO.md`, `docs/ROADMAP.md`, `CHANGELOG.md` und `AGENT_BEHAVIOR_NOTES.md` selbst.
- Kein eigener Task nötig für: Sitzungsnotizen, Status-Updates, TODO-Einträge, Runbook-Korrekturen, Rechtschreib-/Formatierungsfixes.
- Separate Tasks sind weiterhin sinnvoll, wenn die Dokumentationsänderung Teil eines größeren Features ist oder wenn Code geändert wird, der dokumentiert werden muss.
- Ziel: Kontext schonen und kleine dokumentarische Pflegearbeiten nicht durch Task-Erstellung aufblasen.

**Ablauf bei direkten Dokumentations-Edits:**

1. **Vor dem Edit prüfen**, ob aktuell Kanban-Tasks laufen:
   - `kanban task list` aufrufen.
   - Wenn Tasks in `in_progress` oder `review` sind, die dieselben Dokumentationsdateien berühren könnten, mit dem Edit warten.
   - Grund: Worktree-Änderungen werden in `main` gemerged; laufende Tasks könnten uncommittede Doc-Änderungen überschreiben oder Konflikte erzeugen.
2. **Dokumentation editieren** (nur reine Doku, kein Code).
3. **Sofort committen** nach dem Edit:
   - `git add <doku-dateien>`
   - `git commit -m "docs(...): ..."`
   - Niemals Doc-Änderungen uncommitted liegen lassen, wenn anschließend Tasks gestartet werden.
4. **Erst danach neue Kanban-Tasks anlegen/starten**, die auf dem aktuellen, committeden Stand aufbauen.

---

## Quick checklist (copy before committing)

```markdown
- [ ] ADRs reviewed / updated
- [ ] Notes reviewed / updated
- [ ] `docs/TODO.md` reviewed / updated
- [ ] `pytest tests/` green
- [ ] Changes limited to worktree
- [ ] No long-running tasks are blocking the agent
- [ ] Auto-Review enabled + commit mode (wenn neue Dateien erstellt)
- [ ] Wiederkehrende Patterns → neue Regel in dieser Datei
- [ ] Relative Gitea-Release-Links auf `src/tag/<version>/...` prüfen
- [ ] Bei Merge-Problemen: Worktree-Ergebnisse vom Kanban-Sidebar-Agent ins Haupt-Repo übernehmen lassen
- [ ] Nach `task done` geprüft, ob Dateien in `main` vorhanden sind (`git log`)
- [ ] Dokumentation (Notes/Runbooks/TODO) ggf. direkt vom Sidebar-Agent gepflegt
```

**When in doubt: document first, code second, test always.**

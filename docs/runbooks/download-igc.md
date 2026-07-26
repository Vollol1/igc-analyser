> [!TIP]
> Vor jedem Lauf prüfe:
> - [ ] `.env` liegt vor und enthält gültige Credentials (nicht committet).
> - [ ] `venv` ist eingerichtet und Abhängigkeiten installiert.
> - [ ] Zielverzeichnisse (`data/igc/`, `data/processed/`, `data/logs/`) existieren oder werden automatisch angelegt.

# Runbook: IGC-Dateien von dhv-xc.de herunterladen

Schritt-für-Schritt-Anleitung für das Herunterladen von Paragliding-Flugtracks im IGC-Format.

---

## 1. Voraussetzungen

1. Repository liegt lokal vor:
   ```bash
   cd /home/florian/git.vollol.com/fknab/igc-extractor
   ```

2. Virtuelles Environment ist vorhanden:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. `.env` wurde aus `.env.example` erstellt und enthält gültige Werte:
   ```bash
   cp .env.example .env
   # .env bearbeiten
   ```

   Minimale Inhalte:
   ```bash
   DHV_XC_USERNAME=dein_benutzername
   DHV_XC_PASSWORD=dein_passwort
   # optional:
   # DHV_XC_PILOT_ID=12345
   # DHV_XC_BASE_URL=https://www.dhv-xc.de
   ```

   > **Wichtig:** `.env` niemals in Git committen.

---

## 2. Trockenlauf (Dry-Run)

Zeigt, welche Flüge verarbeitet würden, ohne Dateien herunterzuladen.

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/igc_extractor.py \
  --flights 10 \
  --dry-run
```

Erwartete Ausgabe:
- Anzahl der gefundenen Flüge.
- Liste der geplanten Downloads.
- Keine neuen Dateien in `data/igc/`.

---

## 3. Flugliste extrahieren

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/list_flights.py
```

Ausgabe:
- `data/processed/flights.jsonl` mit allen gefundenen Flügen.
- Log unter `data/logs/list_flights_<run_id>.log`.

Dieser Schritt ist optional, wenn `igc_extractor.py` die Flugliste intern selbst baut. Er wird empfohlen, um die Rohdaten zu überprüfen.

---

## 4. IGC-Dateien herunterladen

### 4.1 Erstladen

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/igc_extractor.py \
  --flights 200
```

- Lädt maximal 200 Flüge herunter.
- Speichert `.igc`-Dateien in `data/igc/`.
- Schreibt Status in `data/igc_extractor.db`.
- Protokolliert den Lauf nach `data/logs/`.

### 4.2 Lauf fortsetzen (Resume)

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/igc_extractor.py \
  --flights 200 \
  --resume
```

Bereits vorhandene Flüge werden übersprungen; fehlgeschlagene werden erneut versucht.

---

## 5. Import und Validierung

Nach dem Download in die SQLite-Datenbank importieren:

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/import_flights.py
```

Eingaben:
- `data/processed/flights.jsonl`
- `data/igc/*.igc`

Ausgaben:
- `data/igc_extractor.db` (Tabellen `flights`, `flight_stats`)
- `data/export/flights_overview.json`
- Log unter `data/logs/import_flights_<run_id>.log`

---

## 6. Fehlerbehebung

| Symptom | Mögliche Ursache | Lösung |
|---------|------------------|--------|
| `Login failed` | Falscher Benutzername/Passwort; Account erfordert DHV-Portal-Flow | Credentials prüfen; ggf. im Browser einmalig anmelden und `PHPSESSID` wiederverwenden |
| `403 Forbidden` | CSRF-Token fehlt oder ungültig | Token-Regex in `scripts/list_flights.py` prüfen |
| Leere Flugliste | Falsche Pilot-ID; Filter nicht gesetzt | `--pilot-id` oder `DHV_XC_PILOT_ID` prüfen; Filter `mine=1`/`incpriv=1` prüfen |
| Downloads abbrechen | Netzwerk, Rate-Limit, Server-Fehler | Mit `--resume` erneut starten; Logs prüfen |
| `invalid` IGC-Dateien | Datei unvollständig oder Logger ohne G-Record | Validierungskriterien in `docs/notes/pipeline-notes.md` prüfen |

---

## 7. Monitoring eines längeren Laufs

Bei vielen hundert Flügen empfiehlt es sich, den Prozess im Hintergrund zu starten:

```bash
nohup /home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/igc_extractor.py \
  --flights 500 \
  --resume \
  > /home/florian/git.vollol.com/fknab/igc-extractor/data/logs/igc_download_$(date -u +%Y%m%dT%H%M%SZ).log 2>&1 &
```

Log folgen:

```bash
tail -f /home/florian/git.vollol.com/fknab/igc-extractor/data/logs/igc_download_*.log
```

Stoppen:

```bash
pkill -f igc_extractor.py
```

---

## 8. Checkliste nach dem Lauf

- [ ] `data/igc/` enthält die erwartete Anzahl `.igc`-Dateien.
- [ ] `data/processed/flights.jsonl` ist aktuell.
- [ ] `data/igc_extractor.db` wurde aktualisiert.
- [ ] `import_flights.py` meldet keine unerwarteten `invalid`-Status.
- [ ] `data/export/flights_overview.json` ist vorhanden.
- [ ] Keine `.env` oder Log-Dateien wurden committet.

---

## Verwandte Dokumente

- [Agent-Verhaltensregeln](../../../../../../../AGENT_BEHAVIOR_NOTES.md)
- [Pipeline-Notizen](../pipeline-notes.md)
- [dhv-xc API-Notizen](../dhv-xc-api.md)
- [ADR-001: Architecture & Tech Stack](../../decisions/ADR-001-architecture-techstack.md)

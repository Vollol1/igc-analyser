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

## 2. Flugliste extrahieren

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/list_flights.py
```

Ausgabe:
- `data/processed/flights.jsonl` mit allen gefundenen Flügen.
- Log unter `data/logs/list_flights_<run_id>.log`.

Dieser Schritt ist Voraussetzung für `download_igc.py`. Er schreibt die Felder
`IDFlight`, `FlightDate`, `TakeoffLocation`, `Glider`, `BestTaskDistance`,
`FlightDuration`, `IgcUrl` und `ExtractedAt`.

---

## 3. IGC-Dateien herunterladen

### 3.1 Erstladen

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/download_igc.py
```

- Liest `data/processed/flights.jsonl`.
- Meldet sich mit demselben Session-/CSRF-Login wie `list_flights.py` an.
- Lädt jede `.igc`-Datei seriell über `/flight/{IDFlight}/igc` herunter.
- Speichert `.igc`-Dateien in `data/igc/`.
- Protokolliert den Lauf nach `data/logs/download_igc_<run_id>.log`.
- Schreibt ein Summary nach `data/logs/download_igc_summary_<run_id>.json`.

### 3.2 Lauf fortsetzen / einschränken

Bereits vorhandene Dateien werden standardmäßig übersprungen:

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/download_igc.py
```

Mit `--force` werden alle Dateien neu heruntergeladen:

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/download_igc.py \
  --force
```

Rate-Limiting und Retries können angepasst werden:

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/download_igc.py \
  --rate-limit 2.0 \
  --max-retries 5
```

---

## 4. Import und Validierung

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

## 5. Fehlerbehebung

| Symptom | Mögliche Ursache | Lösung |
|---------|------------------|--------|
| `Login failed` | Falscher Benutzername/Passwort; Account erfordert DHV-Portal-Flow | Credentials prüfen; ggf. im Browser einmalig anmelden und `PHPSESSID` wiederverwenden |
| `403 Forbidden` | CSRF-Token fehlt oder ungültig | Token-Regex in `scripts/dhv_xc_client.py` prüfen |
| Leere Flugliste | Falsche Pilot-ID; Filter nicht gesetzt | `--pilot-id` oder `DHV_XC_PILOT_ID` prüfen; Filter `mine=1`/`incpriv=1` prüfen |
| Downloads abbrechen | Netzwerk, Rate-Limit, Server-Fehler | Mit `--resume` erneut starten; Logs prüfen |
| `invalid` IGC-Dateien | Datei unvollständig oder Logger ohne G-Record | Validierungskriterien in `docs/notes/pipeline-notes.md` prüfen |

---

## 6. Monitoring eines längeren Laufs

Bei vielen hundert Flügen empfiehlt es sich, den Prozess im Hintergrund zu starten:

```bash
nohup /home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/download_igc.py \
  > /home/florian/git.vollol.com/fknab/igc-extractor/data/logs/igc_download_$(date -u +%Y%m%dT%H%M%SZ).log 2>&1 &
```

Log folgen:

```bash
tail -f /home/florian/git.vollol.com/fknab/igc-extractor/data/logs/download_igc_*.log
```

Stoppen:

```bash
pkill -f download_igc.py
```

---

## 7. Checkliste nach dem Lauf

- [ ] `data/igc/` enthält die erwartete Anzahl `.igc`-Dateien.
- [ ] `data/processed/flights.jsonl` ist aktuell.
- [ ] `data/igc_extractor.db` wurde aktualisiert.
- [ ] `import_flights.py` meldet keine unerwarteten `invalid`-Status.
- [ ] `data/export/flights_overview.json` ist vorhanden.
- [ ] Keine `.env` oder Log-Dateien wurden committet.

---

## Verwandte Dokumente

- [Agent-Verhaltensregeln](../../AGENT_BEHAVIOR_NOTES.md)
- [Pipeline-Notizen](../notes/pipeline-notes.md)
- [dhv-xc API-Notizen](../notes/dhv-xc-api.md)
- [ADR-001: Architecture & Tech Stack](../decisions/ADR-001-architecture-techstack.md)

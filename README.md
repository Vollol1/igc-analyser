# igc-extractor

Ein schlankes Python-CLI-Tool zum Herunterladen von Paragliding-Flugtracks im IGC-Format von [dhv-xc.de](https://www.dhv-xc.de). Es wurde entwickelt, um beispielsweise die neuesten 200 Flüge eines Piloten lokal, idempotent und reproduzierbar zu extrahieren, ohne externe Cloud-Dienste zu benötigen.

## Zweck

- Anmelden bei [dhv-xc.de](https://www.dhv-xc.de).
- Auslesen der Flugliste eines Piloten.
- Herunterladen der zugehörigen `.igc`-Dateien.
- Lokale Speicherung der Metadaten (SQLite/JSONL) für weitere Analysen.
- Wiederaufsetzbare Ausführung: bereits vorhandene Dateien werden nicht neu geladen, fehlgeschlagene Downloads können erneut versucht werden.

## Ordnerstruktur

```
igc-extractor/
├── data/
│   ├── igc/                  # Heruntergeladene .igc-Dateien
│   ├── processed/            # Generierte JSONL/CSV-Daten
│   ├── logs/                 # Laufzeit-Logs
│   └── igc_extractor.db      # SQLite-Statusdatenbank (Resume / Idempotenz)
├── docs/
│   ├── decisions/            # Architecture Decision Records (ADRs)
│   └── notes/                # Research notes (e.g. dhv-xc API analysis)
├── scripts/
│   ├── igc_extractor.py    # Einstiegspunkt der CLI
│   └── list_flights.py     # Flight list extraction → JSONL
├── .env.example              # Beispiel-Konfiguration (keine echten Werte)
├── .gitignore                # Ausschluss von .env, venv, Logs, DBs, IGCs …
├── requirements.txt          # Python-Abhängigkeiten
└── README.md                 # Diese Datei
```

## Installation

1. Repository klonen:

   ```bash
   git clone /home/florian/git.vollol.com/fknab/igc-extractor
   cd /home/florian/git.vollol.com/fknab/igc-extractor
   ```

2. Virtuelles Environment anlegen und Abhängigkeiten installieren:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

   Benötigt werden mindestens `requests`, `beautifulsoup4` und `lxml`. `python-dotenv` und `tqdm` sind optional, aber für die bequeme `.env`-Workflow bzw. ansprechende Fortschrittsanzeigen empfohlen.

3. Konfigurationsdatei anlegen:

   ```bash
   cp .env.example .env
   # .env jetzt mit einem sicheren Editor bearbeiten
   ```

   In `.env` trägst du deine echten dhv-xc.de-Zugangsdaten ein:

   ```bash
   DHV_XC_USERNAME=dein_benutzername
   DHV_XC_PASSWORD=dein_passwort

   # Optional
   # DHV_XC_BASE_URL=https://www.dhv-xc.de
   # DHV_XC_PILOT_ID=12345
   ```

   > **Wichtig:** `.env` enthält echte Credentials und darf **niemals** in Git committet werden. Siehe [ADR-001](docs/decisions/ADR-001-architecture-techstack.md) und das Vorbild-Projekt [gag-atlas ADR-007](https://github.com/Vollol1/gag-atlas/blob/main/docs/decisions/ADR-007-secrets-management.md).

## Aufrufbeispiele

> Alle Befehle verwenden absichtlich absolute Pfade und das venv-Python, damit sie aus jedem Verzeichnis heraus direkt ausführbar sind.

### Hilfe anzeigen

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python /home/florian/git.vollol.com/fknab/igc-extractor/scripts/igc_extractor.py --help
```

### Trockenlauf (zeigt, welche Flüge geladen würden)

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python /home/florian/git.vollol.com/fknab/igc-extractor/scripts/igc_extractor.py --flights 10 --dry-run
```

### 200 Flüge herunterladen

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python /home/florian/git.vollol.com/fknab/igc-extractor/scripts/igc_extractor.py --flights 200
```

### Lauf fortsetzen (bereits vorhandene Flüge überspringen)

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python /home/florian/git.vollol.com/fknab/igc-extractor/scripts/igc_extractor.py --flights 200 --resume
```

### Credentials über die Kommandozeile überschreiben (nur für lokale Tests, nicht in Scripts/Skripten)

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python /home/florian/git.vollol.com/fknab/igc-extractor/scripts/igc_extractor.py \
  --username "$DHV_XC_USERNAME" \
  --password "$DHV_XC_PASSWORD" \
  --pilot-id 12345 \
  --flights 50
```

### Flugliste als JSONL extrahieren

```bash
/home/florian/git.vollol.com/fknab/igc-extractor/venv/bin/python \
  /home/florian/git.vollol.com/fknab/igc-extractor/scripts/list_flights.py
```

Dieses Skript meldet sich an, liest mit den Filtern *Nur meine Flüge* / *Private
Flüge einschließen* alle eigenen Flüge aus und schreibt sie idempotent nach
`data/processed/flights.jsonl`. Pro Flug werden ID, Datum, Startplatz, Gleitschirm,
Best-Task-Distanz, Flugdauer und die IGC-Download-URL gespeichert. Läufe werden
nach `data/logs/list_flights_<run_id>.log` protokolliert.

## Credentials / Secrets

Credentials werden in dieser Reihenfolge aufgelöst (erste Treffer gewinnt):

1. Kommandozeilenargumente (`--username`, `--password`, `--pilot-id`, `--base-url`).
2. Umgebungsvariablen (`DHV_XC_USERNAME`, `DHV_XC_PASSWORD`, `DHV_XC_BASE_URL`, `DHV_XC_PILOT_ID`).
3. Aus `.env`, sofern `python-dotenv` installiert ist.

- Committe niemals `.env`.
- Schreibe keine Passwörter direkt in Python-Dateien oder Shell-Skripte.
- Sollte ein Secret unbeabsichtigt in die Git-History gelangen: Key sofort rotieren und die History bereinigen (siehe gag-atlas ADR-007).

## Architekturentscheidungen

Die wichtigsten Entscheidungen sind in [docs/decisions/ADR-001-architecture-techstack.md](docs/decisions/ADR-001-architecture-techstack.md) festgehalten:

- **Python + Requests/BeautifulSoup**: schlank, portabel, keine schwere Framework-Abhängigkeit.
- **Lokale SQLite/JSONL**: keine externe Datenbank nötig.
- **Idempotenz & Resume**: gleiche Eingabe führt bei wiederholtem Lauf zum gleichen Ergebnis; unterbrochene Läufe können nahtlos fortgesetzt werden.
- **`.env`-basierte Secrets**: Credentials ausschließlich über Umgebungsvariablen / `.env`, niemals im Code.

Weitere Architektur-Entscheidungen folgen im Verzeichnis [docs/decisions/](docs/decisions/).

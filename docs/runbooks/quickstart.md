> [!IMPORTANT]
> Vor dem ersten Lauf unbedingt den Abschnitt [Hinweis zur Nutzung](#hinweis-zur-nutzung) lesen.

# Quick Start: igc-extractor

Diese Anleitung begleitet dich Schritt für Schritt vom ersten Download bis zur
fertigen Karte und zum ZIP-Export. Sie ist für Windows, macOS und Linux
beschrieben – du brauchst dafür keine IT-Vorkenntnisse, nur etwas Zeit und einen
Texteditor.

`igc-extractor` ist ein **unabhängiges, inoffizielles Community-Tool**. Es lädt
mit deinen persönlichen Zugangsdaten **deine eigenen IGC-Flugdateien** von
[dhv-xc.de](https://www.dhv-xc.de) herunter und verarbeitet sie lokal auf
deinem Rechner.

---

## Inhalt

1. [Hinweis zur Nutzung](#hinweis-zur-nutzung)
2. [Voraussetzungen](#voraussetzungen)
3. [Repository klonen](#repository-klonen)
4. [Virtuelles Environment anlegen](#virtuelles-environment-anlegen)
5. [Abhängigkeiten installieren](#abhängigkeiten-installieren)
6. [`.env` anlegen und befüllen](#env-anlegen-und-befüllen)
7. [Erster vollständiger Lauf](#erster-vollständiger-lauf)
8. [Karte erzeugen und anzeigen](#karte-erzeugen-und-anzeigen)
9. [ZIP-Export erzeugen](#zip-export-erzeugen)
10. [Häufige Probleme / Troubleshooting](#häufige-probleme--troubleshooting)

---

## Hinweis zur Nutzung

`igc-extractor` ist ein **inoffizielles, unabhängiges Community-Tool**. Es steht
in **keiner Verbindung** zu [dhv-xc.de](https://www.dhv-xc.de), dem Deutschen
Hängegleiterverband e.V. (DHV) oder dessen Serviceportal.

Das Tool meldet sich mit **deinen persönlichen dhv-xc.de-Zugangsdaten** an und
lädt ausschließlich **deine eigenen IGC-Flugdateien** herunter. Es greift nicht
auf fremde Accounts oder öffentliche Daten anderer Piloten zu.

**Nutzung auf eigene Gefahr:** Die öffentlich zugänglichen Nutzungsbedingungen
von dhv-xc.de enthalten keine ausdrückliche Regelung zu automatisiertem Zugriff.
Ein Account-Bann oder andere Sanktionen durch den Betreiber sind daher
**nicht ausgeschlossen**. Bitte verwende das Tool verantwortungsvoll, setze
Rate-Limits und starte keine parallelen Massenabfragen.

Bitte beachte stets die aktuellen Nutzungsbedingungen von dhv-xc.de:

- [dhv-xc.de Nutzungsvereinbarung](https://de.dhv-xc.de/info/nutzungsvereinbarung)
- [dhv-xc.de Release-Informationen](https://de.dhv-xc.de/info#relase-infos)

---

## Voraussetzungen

Du brauchst auf jedem Betriebssystem drei Dinge:

1. **Python 3.10 oder höher**
2. **Git**
3. Einen **Terminal / Eingabeaufforderung**

### Windows

- **Python:** Lade Python von [python.org/downloads](https://www.python.org/downloads/) herunter und installiere es. Aktiviere beim Setup-Assistenten die Option **"Add Python to PATH"**.
- **Git:** Lade Git für Windows von [git-scm.com/download/win](https://git-scm.com/download/win) herunter. Standard-Einstellungen übernehmen ist in der Regel ausreichend. Damit ist auch **Git Bash** als Terminal verfügbar.
- **Terminal:** Öffne **Git Bash** (Startmenü → "Git Bash") oder die Eingabeaufforderung (`cmd`). Git Bash ist empfohlen, weil die Befehle dann fast genauso wie unter macOS/Linux aussehen.

> **Prüfen:** Gib in Git Bash oder `cmd` nacheinander ein:
>
> ```bash
> python --version
> git --version
> ```
>
> Beides sollte Versionsnummern ausgeben (z. B. `Python 3.12.4`).

### macOS

- **Python:** Moderne macOS-Versionen bringen meist Python 3 mit. Prüfe es im Terminal:
>
> ```bash
> python3 --version
> ```
>
> Falls keine Version 3.10+ installiert ist, lade Python von
> [python.org/downloads/macos](https://www.python.org/downloads/macos/) herunter
> oder installiere es über [Homebrew](https://brew.sh):
>
> ```bash
> brew install python
> ```
>
- **Git:** Git ist bei macOS oft bereits dabei. Prüfe:
>
> ```bash
> git --version
> ```
>
> Falls nicht vorhanden, installiere Xcode Command Line Tools:
>
> ```bash
> xcode-select --install
> ```
>
- **Terminal:** Öffne **Terminal.app** (Spotlight → "Terminal").

### Linux (z. B. Ubuntu, Debian, Fedora)

- **Python & Git** sind meist vorinstalliert. Prüfe:
>
> ```bash
> python3 --version
> git --version
> ```
>
> Falls etwas fehlt, installiere es über den Paketmanager:
>
> ```bash
> # Debian / Ubuntu
> sudo apt update
> sudo apt install python3 python3-venv python3-pip git
>
> # Fedora
> sudo dnf install python3 python3-virtualenv python3-pip git
> ```
>
- **Terminal:** Öffne das Terminal deiner Distribution (z. B. `gnome-terminal`, `konsole`, `xterm`).

---

## Repository klonen

Wähle auf deinem Rechner einen Ordner, in dem du Projekte ablegst, z. B. deinen
Benutzer-Ordner oder einen `Projects`-Ordner. Im Terminal wechselst du dorthin
und lädst das Repository herunter.

```bash
cd ~
git clone https://github.com/fknab/igc-analyser.git
cd igc-analyser
```

Nach dem Klonen befinden alle Projektdateien im Unterordner `igc-analyser`.
Alle folgenden Befehle setzen voraus, dass du in diesem Ordner bist.

---

## Virtuelles Environment anlegen

Ein virtuelles Environment (kurz: `venv`) ist ein eigener, kleiner Python-
Arbeitsbereich für das Projekt. Dort werden die benötigten Zusatzpakete
installiert, ohne dein System-Python zu verändern.

Führe im Projektordner aus:

```bash
python3 -m venv venv
```

Aktiviere das Environment anschließend:

| Betriebssystem | Befehl |
|----------------|--------|
| Windows (Git Bash / PowerShell / cmd) | `venv\Scripts\activate` |
| macOS / Linux | `source venv/bin/activate` |

Wenn die Aktivierung funktioniert hat, steht am Zeilenanfang des Terminals
meist `(venv)`. Das bedeutet: du arbeitest jetzt innerhalb des virtuellen
Environments.

> **Hinweis für Windows-Nutzer:** Wenn PowerShell meldet, dass Skripte nicht
> ausgeführt werden dürfen, kannst du die Ausführungsrichtlinie temporär
> anpassen:
>
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
>
> Anschließend `venv\Scripts\activate` erneut versuchen. In Git Bash ist diese
> Anpassung nicht nötig.


---

## Abhängigkeiten installieren

Solange das `venv` aktiv ist (du siehst `(venv)` am Prompt), installierst du die
benötigten Python-Pakete:

```bash
pip install -r requirements.txt
```

Das installiert unter anderem:

- `requests` und `beautifulsoup4` für den Login und das Auslesen der Flugliste,
- `lxml` zum Verarbeiten der HTML-Seiten,
- `python-dotenv` damit die Einstellungen aus `.env` automatisch geladen werden,
- `tqdm` für übersichtliche Fortschrittsbalken bei längeren Läufen,
- `reportlab` für die optionale PDF-Zusammenfassung im Export.

---

## `.env` anlegen und befüllen

Die Zugangsdaten für dhv-xc.de werden in einer lokalen Datei namens `.env`
gespeichert. Diese Datei ist vom Git-Repository ausgeschlossen (sie steht in
`.gitignore`) und bleibt somit privat.

1. Kopiere die Beispieldatei:

   ```bash
   cp .env.example .env
   ```

2. Öffne `.env` in einem einfachen Texteditor, z. B.:

   - Windows: Notepad / Notepad++
   - macOS: TextEdit (im reinen Textmodus) oder `nano` im Terminal
   - Linux: `nano`, `gedit` oder dein bevorzugter Editor

3. Trage deine echten dhv-xc.de-Zugangsdaten ein:

   ```dotenv
   DHV_XC_USERNAME=dein_benutzername
   DHV_XC_PASSWORD=dein_passwort
   ```

4. Optional kannst du weitere Werte ergänzen:

   ```dotenv
   # Piloten-ID, falls bekannt (wird sonst automatisch ermittelt)
   # DHV_XC_PILOT_ID=12345

   # Basis-URL, falls sich die Adresse ändert
   # DHV_XC_BASE_URL=https://www.dhv-xc.de

   # Dein Name für Exporte (Karte / ZIP / PDF)
   # PILOT_NAME=Max Mustermann
   ```

> **Wichtig:**
>
> - `.env` enthält dein Passwort. Speichere sie **niemals** in Git, einem
>   Cloud-Speicher oder einem öffentlichen Gist.
> - Wenn du später das Projekt teilst, sende niemals deine `.env` mit.
> - Unter Windows: Achte darauf, dass Notepad die Datei nicht als `.env.txt`
>   speichert. Der Dateiname muss genau `.env` lauten.

---

## Erster vollständiger Lauf

Der Hauptbefehl führt die komplette Pipeline aus:

1. **Flugliste auslesen** (`list_flights.py`)
2. **IGC-Dateien herunterladen** (`download_igc.py`)
3. **Import & Validierung** (`import_flights.py`)

Stelle sicher, dass dein `venv` aktiv ist, und führe aus:

```bash
python scripts/igc_extractor.py
```

Beim ersten Mal passiert Folgendes:

- Das Tool meldet sich mit deinen Credentials bei dhv-xc.de an.
- Es liest alle deine Flüge (inklusive privater Flüge) aus und speichert sie in
  `data/processed/flights.jsonl`.
- Es lädt die zugehörigen `.igc`-Dateien nach `data/igc/`.
- Es importiert Metadaten und IGC-Dateien in `data/igc-extractor.db` und prüft
  jede Datei strukturell (A-, B- und G-Record).

Ein Lauf kann je nach Fluganzahl einige Minuten bis Stunden dauern. Das Tool
arbeitet defensiv mit Pausen zwischen den Downloads, um die Serverlast gering zu
halten. Du kannst den Prozess jederzeit mit `Strg + C` unterbrechen und später
mit `--resume` fortsetzen:

```bash
python scripts/igc_extractor.py --resume
```

### Nur die neuesten N Flüge verarbeiten

Wenn du erst einmal testen möchtest, begrenze die Anzahl:

```bash
python scripts/igc_extractor.py --flights 10
```

### Trockenlauf (zeigt, was passieren würde, ohne etwas herunterzuladen)

```bash
python scripts/igc_extractor.py --flights 10 --dry-run
```

### Einzelne Schritte manuell ausführen

Falls du lieber jeden Schritt einzeln starten möchtest (z. B. um etwas zu
prüfen):

```bash
# 1. Flugliste aktualisieren
python scripts/list_flights.py

# 2. IGC-Dateien herunterladen
python scripts/download_igc.py

# 3. Import und Validierung
python scripts/import_flights.py
```

Detaillierte Informationen zu den einzelnen Skripten findest du in den
spezialisierten Runbooks:

- [Runbook: IGC-Dateien herunterladen](./download-igc.md)
- [Runbook: IGC-Dateien als ZIP exportieren](./export-igc.md)
- [Runbook: Interaktive Flugkarte erzeugen](./export-flight-map.md)


---

## Karte erzeugen und anzeigen

Nachdem die Flugmetadaten und IGC-Dateien vorliegen, kannst du eine interaktive
Karte aller Flüge erzeugen:

```bash
python scripts/export_flight_map.py
```

Das erzeugt eine HTML-Datei unter `data/export/flights_map_<run_id>.html`.

### Karte im Browser öffnen

Die Karte ist eine einzelne HTML-Datei. Du musst sie **nicht** ins Internet
stellen. Öffne sie einfach lokal:

- **Windows / macOS / Linux:** Doppelklick auf die Datei, oder ziehe sie in ein
  Browserfenster.
- **Über die Kommandozeile:**

  ```bash
  # Beispiel: ersetze <run_id> durch den tatsächlichen Dateinamen
  python -m webbrowser "file://$(pwd)/data/export/flights_map_<run_id>.html"
  ```

  Unter Windows mit Git Bash funktioniert `$(pwd)`; in `cmd` verwendest du den
  vollständigen Pfad zur Datei.

Auf der Karte siehst du:

- die Flugtracks als farbige Linien,
- Startplatz-Marker mit Details,
- ein Statistik-Panel mit Fluganzahl, Zeitraum, Gesamtflugzeit und mehr,
- verschiedene Layer (Lokal / XC / Höhenflug, Startplatz, Flugjahr, Gleitschirm).

> **Tipp:** Die Karte lädt Kartenkacheln (Tiles) aus dem öffentlichen Internet.
> Beim ersten Öffnen ist daher eine Internetverbindung nötig; danach können
> Teile davon im Browser-Cache liegen.

---

## ZIP-Export erzeugen

Mit dem Export-Tool packst du alle lokalen IGC-Dateien inklusive Metadaten,
Validierungsstatus und einer übersichtlichen PDF-Zusammenfassung in ein ZIP-
Archiv:

```bash
python scripts/export_igc_zip.py --pilot-name "Max Mustermann"
```

Ersetze `"Max Mustermann"` durch deinen eigenen Namen. Das Archiv landet unter
`data/export/igc_export_<run_id>.zip` und enthält:

- `README.txt` – Deckblatt mit Name, Zeitraum, Anzahl Flüge und Hinweis zur
  Validierung,
- `export_meta.json` – Zusammenfassung als maschinenlesbare JSON-Datei,
- `flights.csv` – Flugtabelle mit allen wichtigen Details,
- `flight_summary.pdf` – Optisch aufbereitete Zusammenfassung,
- die IGC-Dateien mit sprechenden Dateinamen.

Alternativ kannst du auch ein `tar.gz`-Archiv erzeugen:

```bash
python scripts/export_igc_zip.py --format tar.gz --pilot-name "Max Mustermann"
```

> **Wichtig:** Generierte Archive sollten nicht in Git committet werden. Sie
> stehen bereits in `.gitignore`.


---

## Häufige Probleme / Troubleshooting

### `"python" oder "python3" ist nicht erkannt` / `Befehl nicht gefunden`

- **Windows:** Python wurde vermutlich nicht zu PATH hinzugefügt. Installiere
  Python erneut und aktiviere **"Add Python to PATH"**. Alternativ verwende den
  Befehl `py` statt `python`.
- **macOS:** Verwende `python3` statt `python`.
- **Linux:** Installiere `python3` und `python3-venv` über den Paketmanager.

### `pip` ist nicht vorhanden

- **Windows:** Beim Python-Setup die Option "pip" aktivieren und erneut
  installieren.
- **macOS / Linux:**

  ```bash
  python3 -m ensurepip --upgrade
  ```

### `venv\Scripts\activate` funktioniert nicht (Windows)

- Verwende **Git Bash** (`bash` als Terminal). Dort funktioniert der Befehl
  `source venv/bin/activate` wie unter macOS/Linux.
- In PowerShell: Falls eine Fehlermeldung zur Ausführungsrichtlinie kommt, tippe
  `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` und
  bestätige.

### `Login failed` / `403 Forbidden`

- Prüfe Benutzername und Passwort in `.env`.
- Achte auf Tippfehler, Leerzeichen am Anfang/Ende oder falsche Groß-/Kleinschreibung.
- Melde dich einmal im Browser bei dhv-xc.de an, um sicherzustellen, dass der
  Account funktioniert.
- Falls dhv-xc.de das Layout oder den Login-Prozess geändert hat, kann das Tool
  vorübergehend nicht funktionieren. In diesem Fall ein Issue auf GitHub öffnen.

### `.env` scheint nicht geladen zu werden

- Stelle sicher, dass die Datei wirklich `.env` heißt (nicht `.env.txt`).
- Stelle sicher, dass sie im Projekt-Hauptverzeichnis liegt (direkt neben
  `README.md` und `requirements.txt`).
- Prüfe, ob `python-dotenv` installiert ist:

  ```bash
  pip show python-dotenv
  ```

  Falls nicht:

  ```bash
  pip install python-dotenv
  ```

### Leere Flugliste / keine Flüge werden gefunden

- Prüfe, ob du bei dhv-xc.de überhaupt Flüge eingetragen hast.
- Vergewissere dich, dass `.env` die richtigen Credentials enthält.
- Falls du eine Piloten-ID angegeben hast, prüfe, ob sie korrekt ist.

### Downloads brechen ab oder dauern sehr lange

- Das ist normal bei vielen hundert Flügen. Starte den Lauf erneut mit
  `--resume`:

  ```bash
  python scripts/igc_extractor.py --resume
  ```

- Erhöhe die Pausen zwischen Downloads, falls deine Verbindung instabil ist:

  ```bash
  python scripts/igc_extractor.py --rate-limit 2.0 --batch-pause 30
  ```

- Prüfe, ob parallel ein anderer Download oder Streaming läuft.

### `invalid`-Status bei einigen IGC-Dateien

- Einzelne Logger-Dateien enthalten keine G-Record-Zeile oder sind unvollständig.
- Das Tool markiert sie als `invalid`. Meistens sind sie trotzdem noch lesbar.
- Details zur Validierung stehen in `docs/notes/pipeline-notes.md`.

### Karte zeigt keine Tracks

- Prüfe, ob `data/processed/flights.jsonl` existiert.
- Prüfe, ob `data/igc/` die passenden `.igc`-Dateien enthält.
- Führe ggf. nochmals `python scripts/igc_extractor.py` aus, um fehlende Dateien
  nachzuladen.

### Weitere Fragen

Falls etwas anderes nicht funktioniert:

1. Lies das Log in `data/logs/` – dort steht meist die genaue Fehlermeldung.
2. Prüfe die spezialisierten Runbooks:
   - [download-igc.md](./download-igc.md)
   - [export-flight-map.md](./export-flight-map.md)
   - [export-igc.md](./export-igc.md)
3. Öffne ein Issue auf GitHub mit dem betroffenen Befehl und der Fehlermeldung.

---

## Verwandte Dokumente

- [README (Übersicht)](../../README.md)
- [ADR-001: Architecture & Tech Stack](../decisions/ADR-001-architecture-techstack.md)
- [ADR-003: Öffentliches Release und Umgang mit dhv-xc.de](../decisions/ADR-003-public-release-dhv-xc.md)
- [Legal & Release Notes](../notes/legal-release-notes.md)
- [Runbook: IGC-Dateien herunterladen](./download-igc.md)
- [Runbook: IGC-Dateien als ZIP exportieren](./export-igc.md)
- [Runbook: Interaktive Flugkarte erzeugen](./export-flight-map.md)


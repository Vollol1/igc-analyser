# Legal & Release Notes für den öffentlichen Release

Dieses Dokument fasst die Recherche zur rechtlichen und kommunikativen Bewertung eines öffentlichen GitHub-Releases von `igc-extractor` zusammen. Es dient als Entscheidungsgrundlage für [ADR-003: Öffentliches Release und Umgang mit dhv-xc.de](../decisions/ADR-003-public-release-dhv-xc.md).

> **Hinweis:** Dies ist keine Rechtsberatung. Die Einschätzungen basieren auf der öffentlich zugänglichen Dokumentation von dhv-xc.de. Bei Unsicherheiten sollte der Betreiber kontaktiert werden.

---

## Untersuchte Quellen

1. [dhv-xc.de Nutzungsvereinbarung](https://de.dhv-xc.de/info/nutzungsvereinbarung) — Stand der Analyse: 2026-08-19
2. [dhv-xc.de Release-Informationen](https://de.dhv-xc.de/info#relase-infos) — Stand der Analyse: 2026-08-19

---

## 1. Nutzungsvereinbarung

### Was geregelt ist

Die Seite "DHV-XC Server Nutzungsvereinbarung" enthält eine **Nutzungsrechtsvereinbarung** in deutscher und englischer Sprache. Im Fokus stehen die Rechte an hochgeladenen Dateien sowie Haftungsfragen:

> "Der User übereignet dem DHV e.V. [...] die hochgeladene Dateien (Fotografien, Grafiken, Texte etc.) mit allen Bezeichnungen. Der User überträgt dem DHV e.V. das unentgeltliche, nicht-ausschließliche und nicht an Dritte übertragbare Recht, die Dateien räumlich, zeitlich und inhaltlich für alle zur Zeit bekannten sowie für alle zukünftigen Nutzungsarten zu nutzen."

> "Der DHV e.V. haftet nur für Schäden, die von ihm selbst, seinen gesetzlichen Vertretern oder seinen Erfüllungsgehilfen durch vorsätzliches oder grob fahrlässiges Verhalten verursacht werden."

### Was für igc-extractor fehlt / relevant wäre

Für die Beurteilung des Tools fehlen folgende Aspekte in der öffentlichen Nutzungsvereinbarung:

- **Keine Regelung zu automatisiertem Zugriff, Scraping, Bots, Skripten oder API-Nutzung.**
- **Keine Erwähnung von Rate-Limits** für Downloads, Login-Versuche oder API-Aufrufe.
- **Keine Auflistung erlaubter oder ausdrücklich untersagter Nutzungsarten** (außer der allgemeinen Rechteübertragung an hochgeladene Inhalte).
- **Keine Hinweise auf mögliche Account-Konsequenzen** bei vermeintlich automatisiertem Zugriff.
- **Keine Definition, was als „eigene" oder „fremde" Daten betrachtet wird** oder ob ein Nutzer seine eigenen IGC-Dateien automatisiert abrufen darf.

### Fazit Nutzungsvereinbarung

Die Vereinbarung schützt primär den Betreiber hinsichtlich hochgeladener Inhalte und beschränkt die Haftung. Sie liefert **keine direkte Erlaubnis und kein direktes Verbot** für das automatisierte Herunterladen eigener Flüge. Damit bleibt die Zulässigkeit unklar.

---

## 2. Release-Informationen

### Inhalt

Die Seite "XC Release Informationen" enthält einen chronologischen Change-Log der DHV-XC-Plattform. Themen sind überwiegend:

- UI-/Layout-Änderungen,
- neue oder angepasste Wertungen/Cups,
- Bugfixes,
- technische Anpassungen (z. B. Upgrade auf PHP 8.3),
- neue Features wie "private Flüge", "Notification Center" oder "Papierkorb".

### Was für igc-extractor fehlt / relevant wäre

- **Keine Hinweise auf Änderungen an öffentlichen APIs**, Rate-Limits oder Login-Mechanismen, die für ein externes Tool relevant wären.
- **Keine Ankündigung einer offiziellen API** oder eines API-Keys.
- **Keine Regelungen zur automatisierten Nutzung** oder zu Sanktionen.
- **Keine Hinweise auf zukünftige Maßnahmen gegen Scraping** oder Account-Sperrungen.

### Interessante technische Beobachtungen

- Am 10.03.2022 wurde dokumentiert: "IGC Dateien können heruntergeladen werden (nur für eingeloggte 'Pilots')". Das bestätigt, dass der IGC-Download ein explizites Feature ist, das für angemeldete Piloten vorgesehen ist.
- Am 22.04.2022: "Login-Session auf 60 Minuten erweitert". Hinweis für das Session-Handling im Client.
- Am 18.08.2022: "Neue Option 'Eingeloggt bleiben' beim Login, mit der man bis zu 3 Monaten eingeloggt bleiben kann". Relevant für die Implementierung der Login-Session, aber nicht für die rechtliche Bewertung.

### Fazit Release-Informationen

Die Release-Notes liefern keine rechtlichen oder technischen Einschränkungen für automatisierte Zugriffe. Sie bestätigen lediglich, dass IGC-Downloads ein für eingeloggte Piloten vorgesehenes Feature ist.

---

## 3. Relevante Punkte für igc-extractor

### Rechtslage / Zulässigkeit

- Es gibt **keine explizite Erlaubnis** für automatisierte Zugriffe.
- Es gibt **kein explizites Verbot** in der öffentlich zugänglichen Nutzungsvereinbarung.
- Das Tool greift **nur mit eigenen Credentials** auf **eigene Flüge** zu und liest **keine fremden Daten** aus.
- Der technische Zugriff entspricht im Prinzip dem, was ein Nutzer über den Browser manuell tun könnte (Login → Flugliste → IGC-Download).
- Die Idempotenz, das Resume und das Rate-Limiting des Tools zielen darauf ab, die Serverlast zu minimieren.

### Rate-Limits / Verhalten

- Öffentlich dokumentierte Rate-Limits existieren nicht.
- Das Tool implementiert daher eigenes defensives Verhalten:
  - konfigurierbares `--rate-limit` in `scripts/download_igc.py`,
  - `--batch-size` / `--batch-pause` in `scripts/igc_extractor.py`,
  - `--max-retries` mit exponentiellem Backoff.
- Empfehlung an Nutzer: nicht in einer Schleife ohne Pausen laufen lassen und nicht gleichzeitig mehrere Instanzen starten.

### Account-Konsequenzen

- Nicht öffentlich dokumentiert.
- Ein Account-Bann ist daher **möglich**, wenn der Betreiber automatisierte Zugriffe als Verstoß gegen interne Richtlinien wertet.
- Dieses Risiko muss in README und Tool-Output kommuniziert werden.

### Brand-Neutralität

- `igc-extractor` darf nicht als offizielles dhv-xc.de- oder DHV-e.V.-Tool erscheinen.
- Keine Verwendung offizieller Logos, Marken oder Design-Elemente.
- Projektbeschreibung muss klar kommunizieren: "inoffizielles Community-Tool für persönliche Flugdaten".


---

## 4. Verbleibende Unsicherheiten

1. **Fehlende explizite Regelung zu automatisiertem Zugriff:** Die Nutzungsvereinbarung regelt nicht, ob und unter welchen Bedingungen automatisierte Skripte erlaubt sind.
2. **Keine Auskunft zu Rate-Limits:** Es ist unklar, ab welcher Last der Betreiber Gegenmaßnahmen ergreift.
3. **Keine offizielle API:** Das Tool nutzt interne Endpoints, die sich jederzeit ändern können; es gibt keinen stabilen Vertrag.
4. **Account-Sperrung:** Es ist unklar, welche Verhaltensweisen bei dhv-xc.de zu einer Sperrung führen und ob das Herunterladen eigener IGC-Dateien dazuzählt.
5. **DSGVO / Datenschutz:** Eigene Flugdaten sind personenbezogen. Das Tool verarbeitet sie lokal; dennoch sollte dokumentiert werden, dass keine Daten an Dritte weitergegeben werden.
6. **AGB-Änderungen:** dhv-xc.de kann die Nutzungsbedingungen jederzeit ändern. Das Tool und die README müssen regelmäßig auf Aktualität geprüft werden.

---

## 5. Empfohlene nächste Schritte

1. **Kontakt mit dhv-xc.de aufnehmen**
   - Kontaktadresse aus dem Impressum: `auswerter@xc.dhv.de`
   - Alternativ das Feedback-Tool auf der F.A.Q.-Seite.
   - Frage: Ist das automatisierte Herunterladen eigener IGC-Dateien mit defensiven Rate-Limits für einen persönlichen, nicht-kommerziellen Use-Case zulässig?

2. **README und Tool-Outputs ergänzen**
   - Prominenter Disclaimer-Block (siehe ADR-003 und Vorschlag unten).
   - Keine offiziellen Logos/Claims.
   - Brand-neutrale Formulierung.

3. **Release-Prüfung etablieren**
   - Vor jedem Release prüfen, ob sich an den öffentlichen Hinweisen etwas geändert hat.
   - Disclaimer-Texte aktuell halten.

---

## 6. Vorgeschlagene Textbausteine für README und Tool-Output

### README-Disclaimer

```markdown
## ⚠️ Hinweis zur Nutzung

`igc-extractor` ist ein **inoffizielles, unabhängiges Community-Tool**. Es steht in
**keiner Verbindung** zu [dhv-xc.de](https://www.dhv-xc.de), dem Deutschen
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
- [Nutzungsvereinbarung](https://de.dhv-xc.de/info/nutzungsvereinbarung)
- [Release-Informationen](https://de.dhv-xc.de/info#relase-infos)
```

### Tool-Output / Log-Hinweis

```text
igc-extractor — inoffizielles Tool für den persönlichen Download eigener IGC-Dateien von dhv-xc.de.
Nicht verbunden mit dhv-xc.de oder dem DHV. Nutzung auf eigene Gefahr.
Ein Account-Bann durch den Betreiber ist möglich. Bitte beachte die aktuellen Nutzungsbedingungen.
```

### Brand-neutrale Kurzbeschreibung

```markdown
igc-extractor ist ein schlankes, lokales Python-CLI-Tool, das Piloten beim persönlichen Backup ihrer eigenen IGC-Flugdateien unterstützt. Es ist kein offizielles Angebot von dhv-xc.de.
```

---

## 7. Links

- [dhv-xc.de Nutzungsvereinbarung](https://de.dhv-xc.de/info/nutzungsvereinbarung)
- [dhv-xc.de Release-Informationen](https://de.dhv-xc.de/info#relase-infos)
- [ADR-003: Öffentliches Release und Umgang mit dhv-xc.de](../decisions/ADR-003-public-release-dhv-xc.md)

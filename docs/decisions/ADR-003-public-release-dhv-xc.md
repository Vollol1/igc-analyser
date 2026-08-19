# ADR-003: Öffentliches Release und Umgang mit dhv-xc.de

## Status

Accepted

## Context

`igc-extractor` meldet sich mit persönlichen Zugangsdaten bei [dhv-xc.de](https://www.dhv-xc.de) an und lädt die eigenen IGC-Flugdateien eines Piloten herunter. Das Tool soll auf GitHub öffentlich verfügbar gemacht werden. Dafür müssen folgende Fragen geklärt und dokumentiert werden:

1. **Rechtliche Zulässigkeit** der Automatisierung gegenüber dhv-xc.de.
2. **Brand-Neutralität**: Das Tool darf nicht als offizielles dhv-xc.de- oder DHV-e.V.-Projekt wahrgenommen werden.
3. **Risikohinweis**: Jeder Nutzer muss verstehen, dass er das Tool auf eigene Gefahr verwendet und ein Account-Bann bei dhv-xc.de möglich ist.

Die Recherche zu den öffentlichen Quellen ist in [`docs/notes/legal-release-notes.md`](../notes/legal-release-notes.md) festgehalten.

## Entscheidung

Wir veröffentlichen `igc-extractor` als Open-Source-Projekt auf GitHub, **aber**:

- Das Projekt tritt **brand-neutral** auf.
- Es wird ein **deutlicher Disclaimer** zur Nutzung auf eigene Gefahr und zur Möglichkeit einer Account-Sperrung gegeben.
- Es werden **keine offiziellen dhv-xc.de- oder DHV-e.V.-Logos, -Namen oder -Claims** verwendet, die den Eindruck einer Billigung erwecken.
- Das Tool kommuniziert klar, dass es eine **inoffizielle, privat entwickelte Hilfsanwendung** ist.
- Wir dokumentieren die verbleibenden rechtlichen Unsicherheiten offen und verweisen Nutzer auf die geltenden Nutzungsbedingungen von dhv-xc.de.

## Begründung

- **Rechtliche Klarheit ist unvollständig**: Die öffentlich zugängliche [Nutzungsvereinbarung](https://de.dhv-xc.de/info/nutzungsvereinbarung) regelt vor allem Rechte an hochgeladenen Dateien und Haftungsbeschränkungen, nicht aber automatisierten Zugriff, Scraping oder API-Nutzung. Die [Release-Informationen](https://de.dhv-xc.de/info#relase-infos) enthalten keine Hinweise auf Rate-Limits, erlaubte/problematische automatisierte Nutzung oder Account-Konsequenzen. Damit bleibt die Frage der ausdrücklichen Erlaubnis unbeantwortet.
- **Eigene Flugdaten herunterladen**: Das Tool greift ausschließlich mit den Credentials des jeweiligen Nutzers auf dessen eigene Flüge zu. Es werden keine fremden Accounts, keine öffentlichen Flugdaten anderer Piloten und keine geschützten Inhalte Dritter ausgelesen.
- **Geringere Serverlast als interaktive Nutzung**: Durch Idempotenz, Resume und Rate-Limiting wird die Last auf dhv-xc.de minimiert; das Tool ist bewusst defensiv konfiguriert.
- **Transparenz reduziert Risiko**: Ein klarer Disclaimer und eine brand-neutrale Kommunikation schützen sowohl den Nutzer (Erkenntnis der eigenen Verantwortung) als auch das Projekt (kein Anschein einer offiziellen Vertretung).

## Konsequenzen

### Positive

- Öffentliche Verfügbarkeit ermöglicht Mitnutzung, Code-Review und externe Beiträge.
- Klare Kommunikation der Unabhängigkeit gegenüber dhv-xc.de vermeidet Verwechslungen und rechtliche Missverständnisse.
- Nutzer werden informiert, bevor sie Zugangsdaten eingeben oder das Tool ausführen.
- Dokumentation der Unsicherheiten schafft Vertrauen und Nachvollziehbarkeit.

### Negative / Risiken

- Die rechtliche Zulässigkeit bleibt bis zur Klärung mit dem Betreiber eine **Unsicherheit**.
- Einzelne Nutzer könnten ihre dhv-xc.de-Accounts gesperrt bekommen, wenn der Betreiber automatisierte Zugriffe als Verstoß wertet.
- Layout- oder API-Änderungen auf dhv-xc.de können die Funktion des Tools jederzeit beeinträchtigen.
- Wir müssen README, Tool-Outputs und ggf. Release-Notes regelmäßig auf den Disclaimer und die Brand-Neutralität prüfen.

## Maßnahmen

1. **README.md**
   - Einen prominenten Hinweisblock einfügen:
     - Dies ist ein inoffizielles, unabhängiges Tool.
     - Keine Verbindung zu dhv-xc.de / Deutscher Hängegleiterverband e.V.
     - Nutzung auf eigene Gefahr; Account-Sperrung möglich.
     - Bitte die geltenden Nutzungsbedingungen von dhv-xc.de beachten.
   - Den Default für `--pilot-name` / `--sender` durch einen neutralen Platzhalter (`<Pilotenname>` bzw. leer/kein Default) ersetzen.

2. **Tool-Outputs**
   - Beim Start von `scripts/igc_extractor.py` und `scripts/list_flights.py` einen kurzen Hinweis ausgeben:
     - inoffizielles Tool,
     - Nutzung auf eigene Gefahr,
     - Account-Sperrung möglich.
   - Den Hinweis auf stderr oder in das Log schreiben, damit er nicht die eigentliche Ausgabe stört.

3. **Projekt-Metadaten**
   - Keine dhv-xc.de- oder DHV-Logos im Repository.
   - Keine Domains/Subdomains verwenden, die wie offizielle dhv-xc.de-Dienste aussehen.
   - Lizenz und README klar als „Community-Tool“ formulieren.

4. **Dokumentation**
   - [`docs/notes/legal-release-notes.md`](../notes/legal-release-notes.md) mit den Rechercheergebnissen aktuell halten.
   - Bei Kontaktaufnahme mit dhv-xc.de das Ergebnis hier und im ADR ergänzen.

## Offene Punkte / Unsicherheiten

- Die [Nutzungsvereinbarung](https://de.dhv-xc.de/info/nutzungsvereinbarung) enthält **keine explizite Regelung** zu automatisiertem Zugriff, Scraping, Bots oder API-Nutzung.
- Es sind **keine Rate-Limits, keine offizielle API-Dokumentation und keine Angaben zu Account-Konsequenzen** für automatisierte Zugriffe öffentlich dokumentiert.
- Unklar bleibt, ob das Herunterladen eigener IGC-Dateien mit eigenen Credentials als zulässige Nutzung gilt oder ob der Betreiber hierfür eine explizite Freigabe verlangt.
- Empfohlener nächster Schritt: Kontakt mit `auswerter@xc.dhv.de` (aus dem Impressum) oder über das Feedback-Tool, um die Erlaubnis für den dokumentierten, defensiven Zugriffsmodus zu erfragen.

## References

- [`docs/notes/legal-release-notes.md`](../notes/legal-release-notes.md)
- [dhv-xc.de Nutzungsvereinbarung](https://de.dhv-xc.de/info/nutzungsvereinbarung)
- [dhv-xc.de Release-Informationen](https://de.dhv-xc.de/info#relase-infos)
- [`docs/decisions/ADR-001-architecture-techstack.md`](./ADR-001-architecture-techstack.md)
- [`docs/ROADMAP.md`](../ROADMAP.md)
- [`docs/TODO.md`](../TODO.md)

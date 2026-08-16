# PDF-Layout-Notizen für Flugbuch-Export

## Datum: 2026-08-16

### Layout-Entscheidungen für `flight_summary.pdf`

Bei der Optimierung der PDF-Ausgabe im `export_igc_zip.py`-Skript wurden folgende Entscheidungen getroffen:

#### 1. Titel und Struktur
- **Haupttitel**: "Flugbuch" (statt "IGC-Flugarchiv - Zusammenfassung")
- **Untertitel**: Zeigt Pilotenname und Zeitraum (z.B. "Florian Knab | 2024-10-06 bis 2026-08-15")
- **Tabellentitel**: "Flugliste" (statt "Flugtabelle")

#### 2. Seitenformat
- **Querformat (A4 landscape)** wird für das gesamte PDF verwendet
- Begründung: Die Flugtabelle mit 9 Spalten benötigt die zusätzliche Breite für bessere Lesbarkeit
- Bei 300+ Flügen erstreckt sich die Tabelle ohnehin über mehrere Seiten

#### 3. Spaltenoptimierung
Die Flugtabelle verwendet folgende Spalten mit optimierten Breiten:

| Spalte | Breite | Beschreibung |
|--------|--------|--------------|
| ID | 1.0 cm | Flug-ID (kompakt) |
| Datum | 1.8 cm | Flugdatum (YYYY-MM-DD) |
| Start | 2.8 cm | Startplatz (mehr Platz für lange Namen) |
| Landung | 2.8 cm | Landeplatz (mehr Platz für lange Namen) |
| Glider | 2.5 cm | Fluggerät |
| Dauer (min) | 1.5 cm | Flugdauer in Minuten |
| Distanz (km) | 1.5 km | BestTaskDistance in km |
| IGC-Datei | 4.5 cm | Dateiname (braucht meisten Platz) |
| Status | 1.8 cm | Validierungsstatus |

**Gesamtbreite**: ~24.2 cm (passt in A4 Querformat mit 1 cm Rändern)

#### 4. Schriftgrößen
- **Header**: 7 pt, fett, weiß auf dunkelblauem Hintergrund
- **Datenzeilen**: 6.5 pt (reduziert von 8 pt für bessere Platzausnutzung)
- **Padding**: 3 pt (reduziert von 4 pt)

#### 5. Datumsformatierung
- Erstellungsdatum wird im lesbaren Format angezeigt: "YYYY-MM-DD HH:MM UTC"
- Beispiel: "2026-08-16 12:53 UTC" (statt ISO-String "2026-08-16T12:53:14.881143+00:00")

#### 6. Wiederholte Header
- `repeatRows=1` sorgt dafür, dass die Header-Zeile auf jeder neuen Seite wiederholt wird
- Wichtig für die Lesbarkeit bei mehrseitigen Tabellen

#### 7. Alternierende Zeilenfarben
- Gerade Zeilen (1-basiert, ab Zeile 2): hellgrauer Hintergrund (RGB: 0.95, 0.95, 0.95)
- Ungerade Zeilen: weißer Hintergrund
- Verbessert die Lesbarkeit bei langen Tabellen

### Bekannte Einschränkungen

1. **Lange IGC-Dateinamen**: Bei sehr langen Dateinamen (mit langen Ortsnamen) kann es zu Zeilenumbrüchen kommen. Dies ist ein Kompromiss zwischen Spaltenbreite und Lesbarkeit.

2. **Schriftgröße 6.5 pt**: Für Personen mit Sehbeeinträchtigungen könnte die Schriftgröße klein sein. Bei Bedarf kann sie auf 7-8 pt erhöht werden, was jedoch zu mehr Seitenumbrüchen führen kann.

### Code-Referenz
- Funktion: `_build_pdf()` in `scripts/export_igc_zip.py`
- Helper-Funktion: `_format_datetime_readable()` für Datumsformatierung

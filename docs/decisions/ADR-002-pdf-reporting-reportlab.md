# ADR-002: PDF-Reporting mit reportlab für den IGC-Export

## Status

Accepted

## Kontext

Ab v0.2.0 soll der IGC-Export-Archiv eine strukturierte PDF-Zusammenfassung enthalten (Deckblatt + Flugtabelle). Die PDF kann für Vereins-/Lizenz-Zwecke (z. B. Höhenflug-Nachweis) genutzt werden und wird parallel zu `README.txt`, `export_meta.json` und `flights.csv` in das ZIP/tar.gz-Archiv geschrieben.

Für die Python-Welt stehen im Wesentlichen zwei Optionen zur Verfügung:

- **reportlab**: Reine Python-Bibliothek, generiert PDFs direkt aus Python-Code.
- **WeasyPrint**: Rendert HTML/CSS zu PDF, basiert auf externen Nicht-Python-Abhängigkeiten (Cairo, Pango, GDK-PixBuf etc.).

## Entscheidung

Wir verwenden `reportlab>=4.0.0` für die PDF-Generierung.

## Begründung

- **Keine externen System-Abhängigkeiten**: reportlab ist reiner Python-Code und lässt sich mit `pip install -r requirements.txt` installieren. WeasyPrint erfordert auf den meisten Systemen zusätzliche C-Bibliotheken, was lokale Installationen und CI erschwert.
- **Leichtgewichtig**: Für einen tabellarischen Export mit Deckblatt ist reportlab ausreichend; wir benötigen kein CSS/HTML-Layout.
- **Reproduzierbarkeit**: Da kein externer Renderer involviert ist, ist die generierte PDF auf verschiedenen Umgebungen deterministischer.
- **Geringe Lernkurve für diesen Anwendungsfall**: Die Platypus-API (`SimpleDocTemplate`, `Table`, `Paragraph`) deckt Deckblatt und Seitenumbrüche bei langen Tabellen ab.

## Konsequenzen

- `reportlab>=4.0.0` wird in `requirements.txt` aufgenommen.
- Die PDF ist funktional und strukturiert, aber bewusst schlicht gehalten (kein komplexes Layout).
- Bei künftigen, sehr komplexen Layout-Anforderungen kann der ADR überprüft und ggf. auf WeasyPrint umgestellt werden.

## Implementierung

- Hilfsfunktion `_build_pdf(meta, flights, pilot_name) -> bytes` in `scripts/export_igc_zip.py`.
- Konstante `PDF_FILENAME = "flight_summary.pdf"`.
- PDF wird sowohl in ZIP (`writestr`) als auch tar.gz (`TarInfo` + `addfile`) eingefügt.

## Verwandte Dokumente

- [`docs/runbooks/export-igc.md`](../runbooks/export-igc.md)
- [`docs/ROADMAP.md`](../ROADMAP.md)
- [`docs/TODO.md`](../TODO.md)

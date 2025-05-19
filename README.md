![cover.png](/static/assets/cover.png)

# Sparkasse to CSV converter

Dieses Tool konvertiert PDF-Kontoauszüge der Sparkasse automatisiert in strukturierte CSV-Dateien zur Weiterverarbeitung, z.B. in Notion oder Excel.

> ⚠️ Der PDF-Parser ist auf das Layout der Sparkassen-Kontoauszüge abgestimmt. Für andere Banken ggf. nicht geeignet.

## 🚀 Schnellstart

### Dependencies installieren

Erstelle ein virtuelles Environment (optional aber empfohlen) und installiere die benötigten Pakete:

```bash
python -m venv venv
source venv/bin/activate  # Bei Windows: venv\Scripts\activate

pip install -r requirements.txt
```


### Projekt klonen und lokal starten

```bash
git clone git@github.com:jannikmenzel/sparkasse-to-csv.git
cd sparkasse-to-csv

flask run
```

Anschließend kannst du die Website im Browser unter [http://127.0.0.1:5000](http://127.0.0.1:5000) aufrufen.

## 📁 Projektstruktur

- `static/` – Web-App files und CSS
- `templates/` – HTML files
- `uploads/` – Upload folder (CSV, PDF)
- `app.py` – Flask application
- `csv_format` – csv formatter für notion databases

## 💡 Entwicklungs-Hinweise

Die Webanwendung ermöglicht es, PDF-Kontoauszüge der Sparkasse hochzuladen und daraus CSV-Dateien zu erzeugen. Der Ablauf sieht wie folgt aus:

1. **Upload**:
   - Nutzer laden über das Web-Interface ein PDF hoch (`/upload` Route).
   - Es wird geprüft, ob die Datei erlaubt ist (`.pdf`).

2. **Datenextraktion**:
   - Die Funktion `extract_data_from_pdf()` nutzt `pdfplumber`, um Wörter samt Koordinaten aus dem PDF zu extrahieren.
   - Es wird anhand der X-Koordinaten gefiltert, welche Texte als Datum und welche als Betrag interpretiert werden.
   - Beide Listen (Datum & Betrag) werden ggf. auf gleiche Länge gebracht.

3. **CSV-Erstellung**:
   - Mit den extrahierten Daten wird eine CSV-Datei erstellt (`save_to_csv()`).
   - Der Dateiname richtet sich nach dem frühesten und spätesten Datum im PDF.

4. **Ergebnisanzeige**:
   - Nach dem Hochladen wird eine HTML-Übersicht mit den Daten und ein Download-Link zur CSV-Datei angezeigt.

5. **Download**:
   - Die Route `/download/<filename>` ermöglicht es, die generierte CSV-Datei herunterzuladen.

## 📬 Kontakt

Bei Fragen oder Vorschlägen kontaktiere mich gerne:

- [jannik.menzel@ifsr.de](mailto:jannik.menzel@ifsr.de)

## Lizenz

Dieses Projekt ist unter der GNU General Public License v3.0 (GPLv3) lizenziert – weitere Details findest du in der Datei `LICENSE`.
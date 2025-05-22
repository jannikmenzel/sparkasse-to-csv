
import csv
import os
from datetime import datetime
import pdfplumber
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_to_csv(transactions, output_filename):
    with open(output_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=["Datum", "Buchungstext", "Betrag"])
        writer.writeheader()
        for row in transactions:
            writer.writerow(row)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        with pdfplumber.open(file_path) as pdf:
            raw_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

        transactions = extract_data_from_text_cleaned(raw_text)

        if not transactions:
            return f"Fehler: Keine gültigen Transaktionen erkannt!", 400

        dates = [t["Datum"] for t in transactions if t["Datum"]]
        date_objects = [datetime.strptime(date, '%d.%m.%Y') for date in dates]
        start_date = min(date_objects) if date_objects else datetime.now()
        end_date = max(date_objects) if date_objects else datetime.now()

        csv_filename = f"Kontoauszug_{start_date.strftime('%m_%Y')}-{end_date.strftime('%m_%Y')}.csv"
        csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_filename)

        save_to_csv(transactions, csv_path)

        return render_template(
            'overview.html',
            data=[(t["Datum"], t["Buchungstext"], t["Betrag"]) for t in transactions],
            csv_filename=csv_filename
        )

    return jsonify({"error": "Invalid file"}), 400

@app.route('/download/<filename>')
def download_csv(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return send_file(str(file_path), as_attachment=True)

def extract_data_from_text_cleaned(text):
    import re
    from text_cleaner import clean_buchungstext

    def is_footer_line(line):
        footer_keywords = [
            "Sparkasse Oberlausitz", "Vorstand", "Telefon", "Fax", "BLZ",
            "Niederschlesien", "www.sparkasse", "HR Nr.", "USt-IdNr.",
            "Anstalt des öffentlichen Rechts", "Frauenstr.", "info@", "Zittau", "Dresden",
            "SWIFT", "BIC", "Sparkassen-Finanzgruppe",
            "Der Kontostand kann", "Wertstellung enthalten", "Anzahl Anlagen"
        ]
        return any(keyword.lower() in line.lower() for keyword in footer_keywords)

    lines = text.splitlines()
    transactions = []
    current = {"Datum": "", "Text": [], "Betrag": ""}
    in_table = False

    for line in lines:
        line = line.strip()

        if not line or is_footer_line(line):
            continue

        if "kontostand am" in line.lower() and "uhr" in line.lower():
            break

        # Start erst bei erster Buchung mit Datum
        if not in_table and re.match(r"\d{1,2}\.\d{1,2}\.\d{4}", line):
            in_table = True

        if not in_table:
            continue

        # Betrag erkennen
        amount_match = re.search(r"(-?\d{1,3}(?:\.\d{3})*,\d{2})$", line)
        if amount_match:
            current["Betrag"] = amount_match.group(1)
            line = line.replace(current["Betrag"], "").strip()

        # Datum erkennen
        date_match = re.match(r"^(\d{1,2}\.\d{1,2}\.\d{4})", line)
        if date_match:
            # Wenn vorher was gesammelt wurde, speichern
            if current["Datum"] and (current["Text"] or current["Betrag"]):
                transactions.append({
                    "Datum": current["Datum"],
                    "Buchungstext": clean_buchungstext(" ".join(current["Text"])),
                    "Betrag": current["Betrag"]
                })
                current = {"Datum": "", "Text": [], "Betrag": ""}

            current["Datum"] = date_match.group(1)
            line = line.replace(current["Datum"], "").strip()

        if line:
            current["Text"].append(line)

    # Letzten Eintrag speichern
    if current["Datum"] and (current["Text"] or current["Betrag"]):
        transactions.append({
            "Datum": current["Datum"],
            "Buchungstext": clean_buchungstext(" ".join(current["Text"])),
            "Betrag": current["Betrag"]
        })

    return transactions

if __name__ == '__main__':
    app.run(debug=True)
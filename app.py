import csv
import os
import re
from datetime import datetime

import pdfplumber
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Set up file upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_data_from_pdf(filename):
    target_x_date = 69
    target_x_min = 530
    target_x_max = 550
    tolerance = 10
    dates = []
    transactions = []

    with pdfplumber.open(filename) as pdf:
        for page in pdf.pages:
            for word in page.extract_words():
                text = word['text']
                x_coord = word['x0']

                if abs(x_coord - target_x_date) < tolerance:
                    match = re.search(r'\d{2}\.\d{2}\.\d{4}', text)
                    if match:
                        dates.append(match.group(0))

                if target_x_min <= x_coord <= target_x_max:
                    match = re.search(r'-?\d{1,3},\d{2}', text)
                    if match:
                        transactions.append(match.group(0))

    max_len = max(len(dates), len(transactions))
    dates.extend([""] * (max_len - len(dates)))
    transactions.extend([""] * (max_len - len(transactions)))

    return dates, transactions


def save_to_csv(dates, transactions, output_filename):
    with open(output_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Datum", "Betrag"])
        for date, transaction in zip(dates, transactions):
            writer.writerow([date, transaction])


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

        # Extract data from the uploaded PDF
        dates, transactions = extract_data_from_pdf(file_path)

        if not dates:
            return jsonify({"error": "No data found in PDF"}), 400

        # Create CSV filename
        date_objects = [datetime.strptime(date, '%d.%m.%Y') for date in dates if date]
        start_date = min(date_objects) if date_objects else datetime.now()
        end_date = max(date_objects) if date_objects else datetime.now()
        csv_filename = f"Kontoauszug_{start_date.strftime('%m_%Y')}-{end_date.strftime('%m_%Y')}.csv"
        csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_filename)

        save_to_csv(dates, transactions, csv_path)

        return render_template('overview.html', data=zip(dates, transactions), csv_filename=csv_filename)
    return None


@app.route('/download/<filename>')
def download_csv(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Ensuring the path is a proper string
    return send_file(str(file_path), as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
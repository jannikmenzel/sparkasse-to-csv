import os
from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO

from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename

from src.pdf_iterator import consolidate_pdf_files, save_transactions_to_csv, save_balances_to_csv

app = Flask(__name__)

# Set up file upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _safe_parse_statement_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%d.%m.%Y')
    except ValueError:
        return None


os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    files = [f for f in request.files.getlist('file') if f and f.filename]
    if not files:
        return jsonify({"error": "No selected file"}), 400

    invalid_files = [f.filename for f in files if not allowed_file(f.filename)]
    if invalid_files:
        return jsonify({"error": "Only PDF files are allowed"}), 400

    saved_paths = []
    for file in files:
        filename = secure_filename(file.filename or '')
        if not filename:
            print(f"Skipping invalid filename: '{file.filename}'")
            continue
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        saved_paths.append(file_path)

    log_buffer = StringIO()
    with redirect_stdout(log_buffer):
        print(f"Received {len(saved_paths)} file(s) for processing.")
        data = consolidate_pdf_files(saved_paths)

    if not data['dates']:
        return jsonify({"error": "No data found in PDFs"}), 400

    date_objects = [
        parsed_date
        for parsed_date in (_safe_parse_statement_date(date) for date in data['dates'])
        if parsed_date is not None
    ]
    start_date = min(date_objects) if date_objects else datetime.now()
    end_date = max(date_objects) if date_objects else datetime.now()

    transactions_csv_filename = f"Kontoauszug_{start_date.strftime('%m_%Y')}-{end_date.strftime('%m_%Y')}.csv"
    transactions_csv_path = os.path.join(UPLOAD_FOLDER, transactions_csv_filename)

    with redirect_stdout(log_buffer):
        save_transactions_to_csv(data['dates'], data['contents'], data['transactions'], transactions_csv_path)
        print(f"Saved transactions CSV: {transactions_csv_filename}")
        balances_csv_filename = "Kontostände.csv"
        balances_path = os.path.join(UPLOAD_FOLDER, balances_csv_filename)
        save_balances_to_csv(data['balances'], balances_path)
        print(f"Saved balances CSV: {balances_csv_filename}")

    processing_log = log_buffer.getvalue().strip()
    transaction_rows = list(zip(data['dates'], data['contents'], data['transactions']))

    return render_template(
        'overview.html',
        transaction_rows=transaction_rows,
        balances=data['balances'],
        transactions_csv=transactions_csv_filename,
        balances_csv=balances_csv_filename,
        processing_log=processing_log,
    )


@app.route('/download/<filename>')
def download_csv(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    # Ensuring the path is a proper string
    return send_file(str(file_path), as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
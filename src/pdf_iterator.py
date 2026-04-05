import csv
import os

try:
    from .extract_file import extract_data_from_pdf
except ImportError:
    from extract_file import extract_data_from_pdf


def consolidate_pdf_files(pdf_paths):
    """Extract and merge transactions and balances from multiple PDF paths."""
    all_dates = []
    all_contents = []
    all_transactions = []
    balances_data = []

    for pdf_path in pdf_paths:
        file_name = os.path.basename(pdf_path)
        print(f"Processing: {file_name}")

        data = extract_data_from_pdf(pdf_path)
        print(f"  Extracted {len(data['dates'])} transactions")

        if data['kontostand_date'] and data['kontostand_balance']:
            balances_data.append({
                "file": file_name,
                "date": data['kontostand_date'],
                "balance": data['kontostand_balance']
            })
            print(f"  Account balance: {data['kontostand_balance']} (as of {data['kontostand_date']})")

        all_dates.extend(data['dates'])
        all_contents.extend(data['contents'])
        all_transactions.extend(data['transactions'])

    return {
        "dates": all_dates,
        "contents": all_contents,
        "transactions": all_transactions,
        "balances": balances_data,
    }

def save_transactions_to_csv(dates, contents, transactions, output_filename):
    with open(output_filename, mode='w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Date', 'Content', 'Transaction'])
        for date, content, transaction in zip(dates, contents, transactions):
            writer.writerow([date, content, transaction])

def save_balances_to_csv(balances_data, output_filename):
    with open(output_filename, mode='w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['File', 'Date', 'Balance'])
        for entry in balances_data:
            writer.writerow([entry['file'], entry['date'], entry['balance']])

def iterate_through_pdfs(pdf_files):
    pdf_paths = [os.path.join(input_folder, pdf) for pdf in pdf_files]
    consolidated = consolidate_pdf_files(pdf_paths)
    
    # Saving
    save_transactions_to_csv(
        consolidated['dates'],
        consolidated['contents'],
        consolidated['transactions'],
        output_csv,
    )
    print(f"\n✓ Saved {len(consolidated['dates'])} consolidated transactions to {output_csv}")
    
    save_balances_to_csv(consolidated['balances'], output_balances_csv)
    print(f"✓ Saved {len(consolidated['balances'])} account balances to {output_balances_csv}")


# execute locally in terminal
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(script_dir, "uploads")
    output_csv = os.path.join(script_dir, "output.csv")
    output_balances_csv = os.path.join(script_dir, "account_balances.csv")
    
    if not os.path.isdir(input_folder):
        print(f"Error: Folder '{input_folder}' does not exist.")
        exit(1)
    
    pdf_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in '{input_folder}'.")
        exit(1)

    print(f"Found {len(pdf_files)} PDF file(s) to process.\n")
    iterate_through_pdfs(pdf_files)

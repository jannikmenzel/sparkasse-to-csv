import csv
import os
import re
import pdfplumber

# todo: look if these settings could help with table extraction bugs
# TABLE_SETTINGS = {
#     "vertical_strategy": "lines",
#     "horizontal_strategy": "lines",
#     "intersection_tolerance": 5,
#     "snap_tolerance": 3,
#     "join_tolerance": 3,
#     "edge_min_length": 3,
#     "min_words_vertical": 2,
#     "min_words_horizontal": 1,
#     "keep_blank_chars": True,
# }

SETTINGS = {
    "account_balance_string": "Kontostand am ",
    "awv_string": "AWV-MELDEPFLICHT BEACHTEN HOTLINE BUNDESBANK: (0800) 1234-111",
    "row_detection_padding": 3
}

class BoundingBox:
    def __init__(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    @classmethod
    def from_cell(cls, cell):
        """Helper to create a BB directly from pdfplumber cell coordinates."""
        if cell is None or len(cell) < 4:
            raise ValueError("Invalid cell format for BoundingBox creation.")
        return cls(cell[0], cell[1], cell[2], cell[3])

    def intersects(self, other, tolerance=0):
        return not (
            self.right + tolerance < other.left - tolerance or
            self.left - tolerance > other.right + tolerance or
            self.bottom + tolerance < other.top - tolerance or
            self.top - tolerance > other.bottom + tolerance
        )

def extract_data_from_pdf(filename):
    rows = extract_rows(filename)

    dates = [row['date'] for row in rows]
    contents = [row['content'] for row in rows]
    transactions = [row['transaction'] for row in rows]

    # postprocessing
    kontostand_date, kontostand_balance, contents, transactions = extract_Kontostand(contents, transactions)
    transactions = [normalize_amount(t) for t in transactions]
    contents = strip_awv_meldepflicht(contents)

    return {
        "dates": dates,
        "contents": contents,
        "transactions": transactions,
        "kontostand_date": kontostand_date,
        "kontostand_balance": kontostand_balance
    }

def extract_rows(filename):
    extracted_rows = []

    with pdfplumber.open(filename) as pdf:
        for page in pdf.pages:
            table = page.find_table()
            if table is None or len(table.rows) < 2:
                print(f"  No tables found on page {page.page_number}.")
                continue

            # Establish column bounding boxes for columns, skipping headers
            cells = table.rows[1].cells
            if len(cells) < 3 or len(cells) > 4:
                print(f"  Unexpected table format on page {page.page_number} of {filename}. Expected between 3 and 4 columns, found {len(cells)}.")
                continue
            
            num_columns = len(cells)
            try:
                if num_columns == 4:
                    # Legacy (Datum, Wert, Erläuterung, Betrag)
                    date_col_bb = BoundingBox.from_cell(cells[0])
                    content_col_bb = BoundingBox.from_cell(cells[2])
                    transaction_col_bb = BoundingBox.from_cell(cells[3])
                else:
                    # Standard (Datum, Erläuterung, Betrag)
                    date_col_bb = BoundingBox.from_cell(cells[0])
                    content_col_bb = BoundingBox.from_cell(cells[1])
                    transaction_col_bb = BoundingBox.from_cell(cells[2])
            except ValueError as e:
                print(f"  Error processing table columns on page {page.page_number} of {filename}: {e}")
                continue
            
            table_bottom = table.bbox[3]

            # -- Aggregate columnwise --
            # Categorize words into columns based on intersection with column
            date_words, content_words, transaction_words = [], [], []
            for word in page.extract_words():
                word_bb = BoundingBox(word['x0'], word['top'], word['x1'], word['bottom'])
                text = word['text']

                if date_col_bb.intersects(word_bb):
                    date_words.append((text, word_bb))
                if content_col_bb.intersects(word_bb):
                    content_words.append((text, word_bb))
                if transaction_col_bb.intersects(word_bb):
                    transaction_words.append((text, word_bb))

            # Fixes BUG
            valid_dates = merge_date_words(date_words)

            # -- Aggregate rowwise --
            # Group contents by row using the top and bottom boundaries of the date entries
            for i, (date_text, date_bb) in enumerate(valid_dates):

                # BBox of current entry row across all columns
                if i + 1 < len(valid_dates):
                    row_bottom = valid_dates[i+1][1].top
                else:
                    row_bottom = table_bottom # Use actual table bottom for the final row
                row_bb = BoundingBox(
                    date_col_bb.left,
                    date_bb.top + SETTINGS["row_detection_padding"],
                    transaction_col_bb.right,
                    row_bottom - SETTINGS["row_detection_padding"]
                )

                row_contents = [text for text, bb in content_words if row_bb.intersects(bb)]
                content_str = " ".join(row_contents)

                # Fixes BUG
                content_str = strip_leading_date(content_str)

                # Fetch matching Transactions
                row_transactions = [text for text, bb in transaction_words if row_bb.intersects(bb)]    
                transaction_str = " ".join(row_transactions)

                extracted_rows.append({
                    "date": date_text,
                    "content": content_str,
                    "transaction": transaction_str
                })
    return extracted_rows

# Bug fixing helpers
def merge_date_words(date_words):
    """Safely merges adjacent word tuples if they form a complete DD.MM.YYYY date."""
    merged = []
    i = 0
    while i < len(date_words):
        text, bb = date_words[i]
        clean_text = text.replace(" ", "")
        
        if re.match(r'^\d{2}\.\d{2}\.\d{4}', clean_text):
            merged.append((clean_text[:10], bb))
            i += 1
            continue
            
        # incomplete date
        if i + 1 < len(date_words):
            next_text, next_bb = date_words[i + 1]
            combined_text = clean_text + next_text.replace(" ", "")
            match = re.match(r'^\d{2}\.\d{2}\.\d{4}', combined_text)
            
            if match:
                # Expand bounding box to encompass both words
                merged_bb = BoundingBox(
                    bb.left, min(bb.top, next_bb.top), 
                    max(bb.right, next_bb.right), max(bb.bottom, next_bb.bottom)
                )
                merged.append((match.group(0), merged_bb))
                i += 2
                continue
                
        # 3. Discard noise or invalid date fragments
        i += 1
        
    return merged

def strip_leading_date(content_str):
    if not isinstance(content_str, str):
        return ""
    date_match = re.match(r'^[0-9.]+', content_str)
    if date_match:
        return content_str[date_match.end():].strip()
    return content_str

# Postprocessing
def extract_Kontostand(contents, transactions):
    last_content = ""
    if contents and isinstance(contents[-1], str):
        last_content = contents[-1]

    match = re.search(
        re.escape(SETTINGS["account_balance_string"]) + r'(\d{2}\.\d{2}\.\d{4})',
        last_content,
    )
    if match:
        date = match.group(1)
        if contents:
            contents[-1] = last_content[:match.start()].strip()

        if transactions:
            parts = transactions[-1].split()
            if len(parts) >= 2:
                amount, acc_balance = parts[0], " ".join(parts[1:])
                transactions[-1] = amount
            else:
                acc_balance = transactions[-1]
                amount = transactions[-1]
        else:
            amount = None
            acc_balance = None

        acc_balance = normalize_amount(acc_balance) if acc_balance else None

        return date, acc_balance, contents, transactions
    return None, None, contents, transactions

def normalize_amount(amount_str):
    """
    Normalize amount format from old d.ddd,dd+- to new (-)d.ddd,dd
    Handles both old and new
    """
    if not amount_str:
        return amount_str
    
    amount_str = amount_str.strip()
    
    # Check for old format with trailing + or -
    if amount_str.endswith('+'):
        # Positive amount, remove trailing +
        return amount_str[:-1].strip()
    elif amount_str.endswith('-'):
        # Negative amount, move - to front
        return '-' + amount_str[:-1].strip()
    
    # Already in new format or no sign
    return amount_str

def strip_awv_meldepflicht(contents):
    return [content.replace(SETTINGS["awv_string"], "").strip() for content in contents]
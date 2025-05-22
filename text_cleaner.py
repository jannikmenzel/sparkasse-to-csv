
import re

def clean_buchungstext(text):
    replacements = {
        "Jrut,t a": ", Jutta",
        "SommeJrut,ta": "Sommer, Jutta",
        "ensoo": "ENSO",
        "|": "",
        "rech.n r": "Rech.Nr.",
        "telekom deutschland gmbh": "Telekom Deutschland GmbH",
        "bochumm": "Bochum",
        "knappschaft-bahn-see": "Knappschaft-Bahn-See",
    }

    text = re.sub(r"\s{2,}", " ", text)
    text = text.replace(" .", ".").replace(" ,", ",").replace(" :", ":")

    for wrong, correct in replacements.items():
        if wrong.lower() in text.lower():
            text = re.sub(re.escape(wrong), correct, text, flags=re.IGNORECASE)

    return text.strip()

import pandas as pd
import os

for file in [os.path.join("uploads", f) for f in os.listdir("uploads") if f.endswith(".csv")]:

    try:
        df = pd.read_csv(file, delimiter=",", skipinitialspace=True)
        print(f"Spalten in {file}:", df.columns)

        df.columns = df.columns.str.strip()

        if "Datum" not in df.columns:
            print(f"Fehler: Spalte 'Datum' nicht in {file} gefunden.")
            continue

        try:
            df["Datum"] = pd.to_datetime(df["Datum"], format="%d.%m.%Y").dt.strftime("%m/%d/%Y")
            print("Datum erfolgreich geändert!")
        except Exception as e:
            print(f"Fehler beim Konvertieren der Datumsspalte in {file}: {e}")
            continue

        dir_name, base_name = os.path.split(file)
        new_filename = os.path.join(dir_name, f"new_{base_name}")

        df.to_csv(new_filename, index=False, sep=";")
        print(f"Neue Datei gespeichert: {new_filename}")

    except Exception as e:
        print(f"Fehler beim Verarbeiten von {file}: {e}")
import csv

input_path = "harmoniQ/harmoniq/db/CSVs/buses_new.csv"
output_path = "harmoniQ/harmoniq/db/CSVs/buses_new_cleaned.csv"

with open(input_path, "r", newline="") as infile:
    reader = csv.DictReader(infile)
    cleaned_rows = []
    for row in reader:
        # Determine control type based on bus type
        if row["type"] == "conso":
            control = "PQ"
        elif row["type"] == "prod":
            control = "PV"
        else:  # ligne
            control = "PQ"

        # Reorder and clean the row
        cleaned_row = {
            "name": row["name"],
            "voltage": row["voltage"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "type": row["type"],
            "control": control
        }
        cleaned_rows.append(cleaned_row)

# Write cleaned data
with open(output_path, "w", newline="") as outfile:
    fieldnames = ["name", "voltage", "latitude", "longitude", "type", "control"]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(cleaned_rows)
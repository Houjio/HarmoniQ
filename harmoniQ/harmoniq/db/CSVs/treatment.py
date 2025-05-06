import csv
from collections import Counter

# Charger les bus
buses = {}
with open('harmoniQ/harmoniq/db/CSVs/buses.csv', newline='', encoding='utf-8') as bus_file:
    reader = csv.DictReader(bus_file)
    for row in reader:
        code = row['name'].strip()
        buses[code] = {
            'latitude': row['latitude'].strip(),
            'longitude': row['longitude'].strip(),
            'type': row['type'].strip().lower(),
            'name': row['name'].strip()
        }

# Étape 1 : Compter les connexions (ordre non important)
connection_counts = Counter()
rows_by_connection = {}

with open('harmoniQ/harmoniq/db/CSVs/lines.csv', newline='', encoding='utf-8') as lines_file:
    reader = csv.DictReader(lines_file)
    for row in reader:
        start_code = row['bus0'].strip()
        end_code = row['bus1'].strip()
        key = tuple(sorted([start_code, end_code]))
        connection_counts[key] += 1

# Étape 2 : Écrire les lignes uniques avec note du nombre de connexions
fieldnames = [
    'transmission_line_id', 'transmission_circuit_id', 'owner', 'province',
    'operating_region', 'number_of_circuits', 'current_type',
    'line_segment_length_km', 'line_segment_length_mi', 'line_length_km', 'line_length_mi',
    'voltage', 'reactance', 'ttc_summer', 'ttc_winter',
    'network_node_name_starting', 'latitude_starting', 'longitude_starting', 'network_node_code_starting',
    'network_node_name_ending', 'latitude_ending', 'longitude_ending', 'network_node_code_ending',
    'notes'
]

seen_keys = set()
line_id = 1

with open('harmoniQ/harmoniq/db/CSVs/lines.csv', newline='', encoding='utf-8') as lines_file, \
     open('harmoniQ/harmoniq/db/CSVs/lignes_display.csv', 'w', newline='', encoding='utf-8') as output_file:

    reader = csv.DictReader(lines_file)
    writer = csv.DictWriter(output_file, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        name = row['name'].strip()
        start_code = row['bus0'].strip()
        end_code = row['bus1'].strip()
        key = tuple(sorted([start_code, end_code]))

        if key in seen_keys:
            continue  # 🔁 Ignorer les doublons inversés
        seen_keys.add(key)

        start = buses.get(start_code)
        end = buses.get(end_code)

        if not start or not end:
            print(f"⚠️ Bus manquant pour la ligne '{name}' : {start_code}, {end_code}")
            continue

        if start['type'] == 'conso' or end['type'] == 'conso':
            print(f"🚫 Ligne ignorée (conso détecté) : {name}")
            continue

        valid_types = {'ligne', 'prod'}
        if start['type'] not in valid_types or end['type'] not in valid_types:
            print(f"⚠️ Ligne ignorée (type non autorisé) : {name} ({start['type']} ↔ {end['type']})")
            continue

        if start['latitude'] == end['latitude'] and start['longitude'] == end['longitude']:
            print(f"ℹ️ Ligne ignorée (coordonnées identiques) : {name}")
            continue

        output_row = {
            'transmission_line_id': line_id,
            'voltage': 80,
            'network_node_code_starting': start_code,
            'network_node_name_starting': start['name'],
            'latitude_starting': start['latitude'],
            'longitude_starting': start['longitude'],
            'network_node_code_ending': end_code,
            'network_node_name_ending': end['name'],
            'latitude_ending': end['latitude'],
            'longitude_ending': end['longitude'],
            'notes': f"{connection_counts[key]}"
        }

        writer.writerow(output_row)
        line_id += 1
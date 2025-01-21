"""Script qui initialise la base de données et la remplit avec des données de référence"""

import requests
import pandas as pd
from io import StringIO

from harmoniq.db.engine import engine, get_db, create_station, get_station_by_iata_id
from harmoniq.db.shemas import SQLBase, StationMeteoCreate


def init_db():
    SQLBase.metadata.create_all(bind=engine)


def fill_weather_stations():
    STATION_URL = "https://dd.weather.gc.ca/observations/doc/swob-xml_station_list.csv"
    db = next(get_db())

    response = requests.get(STATION_URL)
    response.raise_for_status()
    station_df = pd.read_csv(StringIO(response.text))
    station_df = station_df[
        station_df["Province/Territory"] == "Quebec"
    ]  # TODO (check if neighboring provinces should be included)

    for _, row in station_df.iterrows():
        iata_id = row["IATA_ID"]
        station_name = row["Name"]

        # Check if IATA id already exists
        if get_station_by_iata_id(iata_id, db):
            print(f"La station {station_name} existe déjà")
            continue

        print(f"Création de la station {station_name}")
        station = StationMeteoCreate(
            nom=station_name,
            IATA_ID=iata_id,
            WMO_ID=row["WMO_ID"] if pd.notna(row["WMO_ID"]) else None,
            MSC_ID=row["MSC_ID"],
            latitude=row["Latitude"],
            longitude=row["Longitude"],
            elevation_m=row["Elevation(m)"],
            fournisseur_de_donnees=(
                row["Data_Provider"] if pd.notna(row["Data_Provider"]) else None
            ),
            reseau=row["Dataset/Network"] if pd.notna(row["Dataset/Network"]) else None,
            automatic=row["AUTO/MAN"] == "AUTO",
        )
        create_station(station, db)


def main():
    print("Initialisation de la base de données")
    init_db()
    print("Collecte des stations météo")
    fill_weather_stations()


if __name__ == "__main__":
    init_db()

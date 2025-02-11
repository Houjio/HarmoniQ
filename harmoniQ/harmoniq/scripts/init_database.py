"""Script qui initialise la base de données et la remplit avec des données de référence"""

import requests
import pandas as pd
from io import StringIO

from harmoniq.db.engine import engine, get_db, create_station, get_station_by_iata_id
from harmoniq.db.shemas import SQLBase, StationMeteoCreate


def init_db():
    SQLBase.metadata.create_all(bind=engine)


def fill_eoliennes():
    EOLIENNE_URL = "https://ftp.cartes.canada.ca/pub/nrcan_rncan/Wind-energy_Energie-eolienne/wind_turbines_database/Wind_Turbine_Database_FGP.xlsx"
    db = next(get_db())

    response = requests.get(EOLIENNE_URL)
    response.raise_for_status()
    station_df = pd.read_excel(response.content)
    station_df = station_df[
        station_df["Province_Territoire"] == "Québec"
    ] 

    # Get unique "Project Name"
    project_names = station_df["Project Name"].unique()
    for project_name in project_names:
        project_df = station_df[station_df["Project Name"] == project_name]
        average_lat = project_df["Latitude"].mean()
        average_lon = project_df["Longitude"].mean()
        project_capacity = project_df["Total Project Capacity (MW)"]
        
        print(project_df)

def main():
    print("Initialisation de la base de données")
    init_db()
    print("Collecte des éolienne")
    fill_eoliennes()

if __name__ == "__main__":
    init_db()

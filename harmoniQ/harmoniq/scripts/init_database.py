"""Script qui initialise la base de données et la remplit avec des données de référence"""

import requests
import pandas as pd

from harmoniq.db.engine import engine, get_db
from harmoniq.db.schemas import SQLBase
from harmoniq.db import schemas
from harmoniq.db.CRUD import create_eolienne_parc, create_eolienne

import argparse


def init_db(reset=False):
    if reset:
        print("Réinitialisation de la base de données")
        SQLBase.metadata.drop_all(bind=engine)

    SQLBase.metadata.create_all(bind=engine)


def fill_eoliennes():
    EOLIENNE_URL = "https://ftp.cartes.canada.ca/pub/nrcan_rncan/Wind-energy_Energie-eolienne/wind_turbines_database/Wind_Turbine_Database_FGP.xlsx"
    db = next(get_db())

    response = requests.get(EOLIENNE_URL)
    response = requests.get(EOLIENNE_URL)
    response.raise_for_status()
    station_df = pd.read_excel(response.content)
    station_df = station_df[station_df["Province_Territoire"] == "Québec"]

    # Get unique "Project Name"
    project_names = station_df["Project Name"].unique()
    for project_name in project_names:
        try:
            project_df = station_df[station_df["Project Name"] == project_name]
            average_lat = project_df["Latitude"].mean()
            average_lon = project_df["Longitude"].mean()
            project_capacity = project_df["Total Project Capacity (MW)"].unique()
            if len(project_capacity) > 1:
                print(f"Projet {project_name} a plusieurs capacités, c'est suspect")

            project_capacity = project_capacity[0]

            eolienne_parc = schemas.EolienneParcCreate(
                nom=project_name,
                latitude=average_lat,
                longitude=average_lon,
                nombre_eoliennes=len(project_df),
                capacite_total=project_capacity,
            )
            result = create_eolienne_parc(db, eolienne_parc)
            project_id = result.id

            for _, row in project_df.iterrows():
                hub_height = row["Hub Height (m)"]

                if isinstance(hub_height, str) and "-" in hub_height:
                    hub_height = sum(map(int, hub_height.split("-"))) / 2

                commisioning = row["Commissioning"]
                if isinstance(commisioning, str) and "/" in commisioning:
                    commisioning = int(commisioning.split("/")[-1])

                eolienne = schemas.EolienneCreate(
                    eolienne_nom=row["Turbine Identifier"],
                    latitude=row["Latitude"],
                    longitude=row["Longitude"],
                    diametre_rotor=row["Rotor Diameter (m)"],
                    turbine_id=row["Turbine Number"],
                    puissance_nominal=row["Turbine Rated Capacity (kW)"],
                    hauteur_moyenne=hub_height,
                    modele_turbine=row["Manufacturer"] + " " + row["Model"],
                    project_name=project_name,
                    annee_commission=commisioning,
                    eolienne_parc_id=project_id,
                )
                create_eolienne(db, eolienne)
        except Exception as e:
            print(f"Erreur lors de l'ajout du projet {project_name}")
            print(e)
            breakpoint()

        print(f"Projet {project_name} ajouté à la base de données")


def populate_db():
    print("Collecte des éolienne")
    fill_eoliennes()


def main():
    parser = argparse.ArgumentParser(description="Initialise la base de données")
    parser.add_argument(
        "-t", "--test", action="store_true", help="Utilise la base de données de test"
    )
    parser.add_argument(
        "-R", "--reset", action="store_true", help="Réinitialise la base de données"
    )
    parser.add_argument(
        "-p",
        "--populate",
        action="store_true",
        help="Remplit la base de données avec des données de référence",
    )

    args = parser.parse_args()

    print("Initialisation de la base de données")
    init_db(args.reset)

    if args.populate:
        populate_db()


if __name__ == "__main__":
    init_db()

"""Script qui initialise la base de données et la remplit avec des données de référence"""

import requests
import pandas as pd
from pathlib import Path
from pathlib import Path

from harmoniq.db.engine import engine, get_db
from harmoniq.db.schemas import SQLBase
from harmoniq.db import schemas
from harmoniq.db.CRUD import (
    create_eolienne_parc,
    create_eolienne,
    create_bus,
    create_line,
    create_line_type,
    create_thermique,
    create_solaire,
)


import argparse


CURRENT_DIR = Path(__file__).parent
CSV_DIR = CURRENT_DIR / ".." / "db" / "CSVs"


def init_db(reset=False):
    if reset:
        print("Réinitialisation de la base de données")
        SQLBase.metadata.drop_all(bind=engine)

    SQLBase.metadata.create_all(bind=engine)


def fill_thermique():
    df = pd.read_csv(
        CSV_DIR / "centrale_thermique.csv", delimiter=";", encoding="utf-8"
    )

    db = next(get_db())

    for _, row in df.iterrows():
        create_thermique(
            db,
            schemas.ThermiqueCreate(
                nom=row["nom"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                puissance_nominal=row["puissance_MW"],
                type_intrant=row["type"],
                semaine_maintenance=row["semaine_maintenance"],
            ),
        )
        print(f"Centrale {row['nom']} ajoutée à la base de données")


def fill_solaire():
    df = pd.read_csv(
        CSV_DIR / "centrales_solaires.csv", delimiter=";", encoding="utf-8"
    )

    db = next(get_db())

    for _, row in df.iterrows():
        create_solaire(
            db,
            schemas.SolaireCreate(
                nom=row["nom"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                puissance_nominal=row["puissance_nominal_MW"],
                angle_panneau=row["angle_panneau"],
                orientation_panneau=row["orientation_panneau"],  # Correction ici
                nombre_panneau=row["nombre_panneau"],
            ),
        )
        print(f"Centrale solaire {row['nom']} ajoutée à la base de données")


def fill_eoliennes():
    db = next(get_db())

    station_df = pd.read_excel(CSV_DIR / "Wind_Turbine_Database_FGP.xlsx")
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


def fill_line_types():
    """Remplit la table line_type à partir du fichier CSV"""
    from harmoniq.db.schemas import LineType

    db = next(get_db())

    file_path = CSV_DIR / "line_types.csv"
    line_types_df = pd.read_csv(file_path)

    count = 0
    for _, row in line_types_df.iterrows():
        existing = db.query(LineType).filter(LineType.name == row["name"]).first()

        if existing:
            print(f"Type de ligne {row['name']} existe déjà")
            continue

        db_line_type = schemas.LineTypeCreate(
            name=row["name"],
            f_nom=int(row["f_nom"]),
            r_per_length=float(row["r_per_length"]),
            x_per_length=float(row["x_per_length"]),
        )

        create_line_type(db, db_line_type)
        count += 1
        print(f"Type de ligne '{db_line_type.name}' ajouté à la base de données")

    print(f"{count} types de ligne ajoutés à la base de données")


def fill_buses():
    """Remplit la table bus à partir du fichier CSV"""
    db = next(get_db())

    file_path = CSV_DIR / "buses.csv"
    buses_df = pd.read_csv(file_path)

    count = 0
    for _, row in buses_df.iterrows():
        existing = db.query(schemas.Bus).filter(schemas.Bus.name == row["name"]).first()
        if existing:
            print(f"Bus {row['name']} existe déjà")
            continue

        db_bus = schemas.BusCreate(
            name=row["name"],
            v_nom=row["voltage"],
            type=schemas.BusType(row["type"]),
            x=row["longitude"],
            y=row["latitude"],
            control=schemas.BusControlType(row["control"]),
        )

        count += 1
        create_bus(db, db_bus)
        print(f"Bus '{db_bus.name}' ajouté à la base de données")

    print(f"{count} bus ajoutés à la base de données")


def fill_lines():
    """Remplit la table line à partir du fichier CSV"""
    db = next(get_db())

    file_path = CSV_DIR / "lines.csv"
    lines_df = pd.read_csv(file_path)

    count = 0
    for _, row in lines_df.iterrows():
        try:
            existing = (
                db.query(schemas.Line).filter(schemas.Line.name == row["name"]).first()
            )
            if existing:
                print(f"Ligne {row['name']} existe déjà")
                continue

            bus_from = (
                db.query(schemas.Bus).filter(schemas.Bus.name == row["bus0"]).first()
            )
            if not bus_from:
                print(
                    f"Bus de départ {row['bus0']} non trouvé pour la ligne {row['name']}"
                )
                continue

            bus_to = (
                db.query(schemas.Bus).filter(schemas.Bus.name == row["bus1"]).first()
            )
            if not bus_to:
                print(
                    f"Bus d'arrivée {row['bus1']} non trouvé pour la ligne {row['name']}"
                )
                continue

            line_type = (
                db.query(schemas.LineType)
                .filter(schemas.LineType.name == row["type"])
                .first()
            )
            if not line_type:
                print(
                    f"Type de ligne {row['type']} non trouvé pour la ligne {row['name']}"
                )
                continue

            db_line = schemas.LineCreate(
                name=row["name"],
                bus0=row["bus0"],
                bus1=row["bus1"],
                type=row["type"],
                length=row["length"],
                capital_cost=row["capital_cost"],
                s_nom=row["s_nom"],
            )
            count += 1
            create_line(db, db_line)
            print(f"Ligne '{db_line.name}' ajouté à la base de données")
        except Exception as e:
            print(f"Erreur lors de l'ajout de la ligne {row['name']}: {e}")

    print(f"{count} lignes ajoutées à la base de données")


def fill_network():
    """Remplit les tables du réseau électrique (line_type, bus, line)"""
    print("Collecte des types de lignes...")
    fill_line_types()

    print("Collecte des bus...")
    fill_buses()

    print("Collecte des lignes...")
    fill_lines()


def populate_db():
    print("Collecte des éoliennes")
    fill_eoliennes()

    print("Collecte des données du réseau électrique :")
    fill_network()

    print("Collecte des centrales thermiques")
    fill_thermique()

    print("Collecte des centrales solaires")
    fill_solaire()


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

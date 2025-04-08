"""Script qui initialise la base de données et la remplit avec des données de référence"""

import requests
import pandas as pd
from pathlib import Path
from pathlib import Path

from harmoniq.db.engine import engine, get_db
from harmoniq.db.schemas import SQLBase
from harmoniq.db import schemas
from harmoniq.db import CRUD


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
        CRUD.create_thermique(
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
        CRUD.create_solaire(
            db,
            schemas.SolaireCreate(
                nom=row["nom"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                puissance_nominal=row["puissance_nominal_MW"],
                angle_panneau=row["angle_panneau"],
                orientation_panneau=row["orientation_panneau"],
                nombre_panneau=row["nombre_panneau"],
            ),
        )
        print(f"Centrale solaire {row['nom']} ajoutée à la base de données")


def fill_parc_eoliennes():
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

            for _, row in project_df.iterrows():
                hub_height = row["Hub Height (m)"]
                
                if isinstance(hub_height, str) and "-" in hub_height:
                    hub_height = sum(map(int, hub_height.split("-")))/2
                    project_df["Hub Height (m)"] = project_df["Hub Height (m)"].replace(row["Hub Height (m)"], hub_height)
            
            eolienne_parc = schemas.EolienneParcCreate(
                nom=project_name,
                latitude=average_lat,
                longitude=average_lon,
                nombre_eoliennes=len(project_df),
                capacite_total=project_capacity,
                hauteur_moyenne=project_df["Hub Height (m)"].mean(),
                modele_turbine = project_df["Model"].unique()[0],
                puissance_nominal = project_df["Turbine Rated Capacity (kW)"].unique()[0]
            )
            
            CRUD.create_eolienne_parc(db, eolienne_parc)
        except Exception as e:
            print(f"Erreur lors de l'ajout du projet {project_name}")
            print(e)
            breakpoint()

        print(f"Projet {project_name} ajouté à la base de données")


def fill_hydro():
    """Remplit la table bus à partir du fichier CSV"""
    db = next(get_db())

    file_path = CSV_DIR / "Info_Barrages.csv"
    barrages_df = pd.read_csv(file_path)

    count = 0
    for _, row in barrages_df.iterrows():
        existing = (
            db.query(schemas.Hydro).filter(schemas.Hydro.nom == row["Nom"]).first()
        )
        if existing:
            print(f"Barrage {row['Nom']} existe déjà")
            continue

        db_hydro = schemas.HydroCreate(
            nom=row["Nom"],
            puissance_nominal=row["Puissance_Installee_MW"],
            type_barrage=row["Type"],
            latitude=row["Longitude"],
            longitude=row["Latitude"],
            hauteur_chute=row["Hauteur_de_chute_m"],
            debits_nominal=row["Debits_nom"],
            modele_turbine=row["Type_turbine"],
            nb_turbines=row["Nb_turbines"],
            nb_turbines_maintenance=row["nb_turbines_maintenance"],
            volume_reservoir=row["Volume_reservoir"],
            id_HQ=row["id_HQ"],
        )
        count += 1
        CRUD.create_hydro(db, db_hydro)
        print(f"Barrage '{db_hydro.nom}' ajouté à la base de données")

    print(f"{count} barrage ajoutés à la base de données")


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

        CRUD.create_line_type(db, db_line_type)
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
        CRUD.create_bus(db, db_bus)
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
            CRUD.create_line(db, db_line)
            print(f"Ligne '{db_line.name}' ajouté à la base de données")
        except Exception as e:
            print(f"Erreur lors de l'ajout de la ligne {row['name']}: {e}")

    print(f"{count} lignes ajoutées à la base de données")


def create_initial_scenarios():
    scenario_2035 = schemas.ScenarioCreate(
        nom="année 2035",
        description="Scénario de base pour l'année 2035",
        date_de_debut="2035-01-01",
        date_de_fin="2035-12-31",
        pas_de_temps="PT1H",
    )

    db = next(get_db())
    existing = (
        db.query(schemas.Scenario)
        .filter(schemas.Scenario.nom == scenario_2035.nom)
        .first()
    )
    if existing:
        print(f"Scénario {scenario_2035.nom} existe déjà")
    else:
        CRUD.create_scenario(db, scenario_2035)
        print(f"Scénario {scenario_2035.nom} ajouté à la base de données")

    scenario_2050 = schemas.ScenarioCreate(
        nom="année 2050",
        description="Scénario de base pour l'année 2050",
        date_de_debut="2050-01-01",
        date_de_fin="2050-12-31",
        pas_de_temps="PT1H",
    )

    existing = (
        db.query(schemas.Scenario)
        .filter(schemas.Scenario.nom == scenario_2050.nom)
        .first()
    )

    if existing:
        print(f"Scénario {scenario_2050.nom} existe déjà")
    else:
        CRUD.create_scenario(db, scenario_2050)
        print(f"Scénario {scenario_2050.nom} ajouté à la base de données")


def create_initial_groupe_infra():
    # Get all infrastructures
    db = next(get_db())

    eoliennes = CRUD.read_all_eolienne_parc(db)
    hydro = CRUD.read_all_hydro(db)
    thermique = CRUD.read_all_thermique(db)
    solaire = CRUD.read_all_solaire(db)

    to_string = lambda x: ",".join([str(y.id) for y in x])

    chaque_infra = schemas.ListeInfrastructuresCreate(
        nom="Chaque infrastructure",
        parc_eoliens=to_string(eoliennes),
        central_hydroelectriques=to_string(hydro),
        central_thermique=to_string(thermique),
        parc_solaires=to_string(solaire),
    )

    existing = (
        db.query(schemas.ListeInfrastructures)
        .filter(schemas.ListeInfrastructures.nom == chaque_infra.nom)
        .first()
    )
    if existing:
        print(f"Groupe d'infrastructure {chaque_infra.nom} existe déjà")
    else:
        CRUD.create_liste_infrastructures(db, chaque_infra)
        print(f"Groupe d'infrastructure {chaque_infra.nom} ajouté à la base de données")


def check_if_empty():
    db = next(get_db())
    tables = [
        schemas.EolienneParc,
        schemas.Eolienne,
        schemas.Hydro,
        schemas.Bus,
        schemas.Line,
        schemas.LineType,
        schemas.Thermique,
        schemas.Solaire,
        schemas.Scenario,
    ]

    for table in tables:
        if db.query(table).first():
            return False

    return True


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
    fill_parc_eoliennes()

    print("Collecte des données du réseau électrique :")
    fill_network()

    print("Collecte des données du réseau hydro :")
    fill_hydro()

    print("Collecte des centrales thermiques")
    fill_thermique()

    print("Collecte des centrales solaires")
    fill_solaire()

    print("Création des scénarios de base")
    create_initial_scenarios()

    print("Création des groupes d'infrastructure")
    create_initial_groupe_infra()


def main():
    parser = argparse.ArgumentParser(description="Initialise la base de données")
    parser.add_argument(
        "-t", "--test", action="store_true", help="Utilise la base de données de test"
    )
    parser.add_argument(
        "-R", "--reset", action="store_true", help="Réinitialise la base de données"
    )
    parser.add_argument(
        "-f",
        "--fill",
        action="store_true",
        help="Remplit la base de données si elle est vide",
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

    if args.fill:
        if check_if_empty():
            populate_db()
        else:
            print("La base de données est déjà remplie")

    if args.populate:
        populate_db()


if __name__ == "__main__":
    populate_db()
    init_db()

"""
engine.py
------
Le moteur est ce qui connecte votre code à la base de données :
- Ouvre et gère les connexions à la base.
- Sait parler le langage de la base de données (SQL pour SQLite).
- Est utilisé par chaque session pour exécuter des requêtes et sauvegarder ou charger des données.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import inspect
from typing import Dict
import pandas as pd

from harmoniq import DB_PATH
from harmoniq.db import schemas

DATABASE__URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE__URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _get_sql_tables(schemas_module) -> Dict[type, Dict[str, type]]:
    all_classes = [member for _, member in inspect.getmembers(schemas_module, inspect.isclass)]
    # We can also make a liste of all the real classes meaning objects representing the tables 
    base_classes = [
        cls
        for cls in all_classes
        if issubclass(cls, schemas.SQLBase) and cls is not schemas.SQLBase
    ]
    # Get corresponding pydantic, create and response classes
    sql_tables = {}
    for cls in base_classes:
        base_class = [c for c in all_classes if c.__name__ == f"{cls.__name__}Base"][0]
        create_class = [
            c for c in all_classes if c.__name__ == f"{cls.__name__}Create"
        ][0]
        response_class = [
            c for c in all_classes if c.__name__ == f"{cls.__name__}Response"
        ][0]
        sql_tables[cls] = {
            "base": base_class,
            "create": create_class,
            "response": response_class,
        }
    return sql_tables

#In this there are four types of classes , base ones (from pydantic), create ones (for creating new objects) and response ones (for returning the data)
sql_tables = _get_sql_tables(schemas)

"""Example: print(sql_tables)
{
<class 'harmoniq.db.schemas.Bus'>: {'base': <class 'harmoniq.db.schemas.BusBase'>, 'create': <class 'harmoniq.db.schemas.BusCreate'>, 'response': <class 'harmoniq.db.schemas.BusResponse'>}, 
<class 'harmoniq.db.schemas.EolienneParc'>: {'base': <class 'harmoniq.db.schemas.EolienneParcBase'>, 'create': <class 'harmoniq.db.schemas.EolienneParcCreate'>, 'response': <class 'harmoniq.db.schemas.EolienneParcResponse'>}, 
<class 'harmoniq.db.schemas.Hydro'>: {'base': <class 'harmoniq.db.schemas.HydroBase'>, 'create': <class 'harmoniq.db.schemas.HydroCreate'>, 'response': <class 'harmoniq.db.schemas.HydroResponse'>}, 
<class 'harmoniq.db.schemas.Line'>: {'base': <class 'harmoniq.db.schemas.LineBase'>, 'create': <class 'harmoniq.db.schemas.LineCreate'>, 'response': <class 'harmoniq.db.schemas.LineResponse'>}, 
<class 'harmoniq.db.schemas.LineType'>: {'base': <class 'harmoniq.db.schemas.LineTypeBase'>, 'create': <class 'harmoniq.db.schemas.LineTypeCreate'>, 'response': <class 'harmoniq.db.schemas.LineTypeResponse'>}, 
<class 'harmoniq.db.schemas.ListeInfrastructures'>: {'base': <class 'harmoniq.db.schemas.ListeInfrastructuresBase'>, 'create': <class 'harmoniq.db.schemas.ListeInfrastructuresCreate'>, 'response': <class 'harmoniq.db.schemas.ListeInfrastructuresResponse'>}, 
<class 'harmoniq.db.schemas.Nucleaire'>: {'base': <class 'harmoniq.db.schemas.NucleaireBase'>, 'create': <class 'harmoniq.db.schemas.NucleaireCreate'>, 'response': <class 'harmoniq.db.schemas.NucleaireResponse'>}, 
<class 'harmoniq.db.schemas.Scenario'>: {'base': <class 'harmoniq.db.schemas.ScenarioBase'>, 'create': <class 'harmoniq.db.schemas.ScenarioCreate'>, 'response': <class 'harmoniq.db.schemas.ScenarioResponse'>},
<class 'harmoniq.db.schemas.Solaire'>: {'base': <class 'harmoniq.db.schemas.SolaireBase'>, 'create': <class 'harmoniq.db.schemas.SolaireCreate'>, 'response': <class 'harmoniq.db.schemas.SolaireResponse'>}, 
<class 'harmoniq.db.schemas.Thermique'>: {'base': <class 'harmoniq.db.schemas.ThermiqueBase'>, 'create': <class 'harmoniq.db.schemas.ThermiqueCreate'>, 'response': <class 'harmoniq.db.schemas.ThermiqueResponse'>}
}
"""

#Launch the session where we have the database that will evolve (it is like a dataholder where commands from the API and data will be stored and interact)

def get_db():
    """
    Crée une session de base de données pour interagir avec la base de données.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Get all MRCs , MRC stands for Municipalité Régionale de Comté

def get_all_mrcs_population(db: Session, mrc_id: int) -> pd.DataFrame:
    data = (
        db.query(schemas.InstancePopulation)
        .filter(schemas.InstancePopulation.mrc_id == mrc_id)
        .all()
    )

    df = pd.DataFrame(
        [{"annee": item.annee, "population": item.population} for item in data]
    )
    return df

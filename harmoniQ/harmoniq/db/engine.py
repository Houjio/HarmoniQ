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


def _get_sql_tables(module) -> Dict[type, Dict[str, type]]:
    all_classes = [member for _, member in inspect.getmembers(module, inspect.isclass)]
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


sql_tables = _get_sql_tables(schemas)


def get_db():
    """
    Crée une session de base de données pour interagir avec la base de données.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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

from sqlalchemy import create_engine
import sqlalchemy
from sqlalchemy.sql import func
from sqlalchemy.orm import Session, sessionmaker

from harmoniq import DB_PATH
from harmoniq.db.shemas import *

DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Crée une session de base de données pour interagir avec la base de données.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_station(station: StationMeteoCreate, db: Session):
    """
    Crée un nouvel enregistrement de station météo dans la base de données.

    Args:
        station (StationMeteoCreate): Les données requises pour créer une nouvelle station météo.
        db (Session): La session de base de données utilisée pour interagir avec la base de données.

    Returns:
        StationMeteo: Le nouvel enregistrement de station météo créé.
    """
    db_station = StationMeteo(**station.model_dump())
    db.add(db_station)
    db.commit()
    db.refresh(db_station)
    return db_station


def delete_station(station_id: int, db: Session) -> None:
    """
    Supprime un enregistrement de station météo de la base de données.

    Args:
        station_id (int): L'identifiant de la station météo à supprimer.
        db (Session): La session de base de données utilisée pour interagir avec la base de données.
    """
    db.query(StationMeteo).filter(StationMeteo.id == station_id).delete()
    db.commit()


def get_all_stations(db: Session):
    """
    Récupère toutes les stations météo de la base de données.

    Args:
        db (Session): La session de base de données utilisée pour interagir avec la base de données.
    """
    return db.query(StationMeteo).all()


def get_station_by_id(station_id: int, db: Session):
    """
    Récupère une station météo à partir de son identifiant.

    Args:
        station_id (int): L'identifiant de la station météo à récupérer.
        db (Session): La session de base de données utilisée pour interagir avec la base de données.
    """
    return db.query(StationMeteo).filter(StationMeteo.id == station_id).first()


def get_station_by_iata_id(iata_id: str, db: Session):
    """
    Récupère une station météo à partir de son identifiant IATA.

    Args:
        iata_id (str): L'identifiant IATA de la station météo à récupérer.
        db (Session): La session de base de données utilisée pour interagir avec la base de données.
    """
    return db.query(StationMeteo).filter(StationMeteo.IATA_ID == iata_id).first()


def get_n_nearest_stations(latitude: float, longitude: float, n: int, db: Session):
    """
    Récupère les n stations météo les plus proches d'un point donné.

    Args:
        latitude (float): La latitude du point de référence.
        longitude (float): La longitude du point de référence.
        n (int): Le nombre de stations à récupérer.
        db (Session): La session de base de données utilisée pour interagir avec la base de données.
    """
    latitude_radians = func.radians(latitude)
    longitude_radians = func.radians(longitude)

    return (
        db.query(StationMeteo)
        .order_by(
            func.acos(
                func.sin(latitude_radians)
                * func.sin(func.radians(StationMeteo.latitude))
                + func.cos(latitude_radians)
                * func.cos(func.radians(StationMeteo.latitude))
                * func.cos(func.radians(StationMeteo.longitude) - longitude_radians)
            )
        )
        .limit(n)
        .all()
    )

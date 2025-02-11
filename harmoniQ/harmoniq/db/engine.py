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
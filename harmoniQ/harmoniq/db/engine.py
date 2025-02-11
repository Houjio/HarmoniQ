from sqlalchemy import create_engine
import sqlalchemy
from sqlalchemy.sql import func
from sqlalchemy.orm import Session, sessionmaker
from typing import Optional

from harmoniq import DB_PATH
from harmoniq.db import shemas

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

def create_eolienne(db: Session, eolienne: shemas.EolienneCreate):
    db_eolienne = shemas.Eolienne(**eolienne.dict())
    db.add(db_eolienne)
    db.commit()
    db.refresh(db_eolienne)
    return db_eolienne

def read_eoliennes(db: Session, id: Optional[int] = None):
    if id is not None:
        return db.query(shemas.Eolienne).filter(shemas.Eolienne.id == id).all()
    return db.query(shemas.Eolienne).all()

def read_eolienne(db: Session, eolienne_id: int):
    eolienne = db.query(shemas.Eolienne).filter(shemas.Eolienne.id == eolienne_id).first()
    return eolienne

def update_eolienne(db: Session, eolienne_id: int, eolienne: shemas.EolienneCreate):
    db_eolienne = db.query(shemas.Eolienne).filter(shemas.Eolienne.id == eolienne_id).first()
    if db_eolienne is None:
        return None
    for key, value in eolienne.dict().items():
        setattr(db_eolienne, key, value)
    db.commit()
    db.refresh(db_eolienne)
    return db_eolienne

def delete_eolienne(db: Session, eolienne_id: int):
    db_eolienne = db.query(shemas.Eolienne).filter(shemas.Eolienne.id == eolienne_id).first()
    if db_eolienne is None:
        return None
    db.delete(db_eolienne)
    db.commit()
    return {"message": "Eolienne deleted successfully"}

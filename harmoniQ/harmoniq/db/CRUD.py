from sqlalchemy import Table
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from harmoniq.db.engine import sql_tables


def read_all_data(db: Session, table: Table):
    return db.query(table).all()


def create_data(db: Session, table: Table, data: BaseModel):
    db_data = table(**data.dict())
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    return db_data


def read_data_by_id(db: Session, table: Table, id: int):
    return db.query(table).filter(table.id == id).first()

def read_multiple_by_id(db: Session, table: Table, ids: List[int]):
    return db.query(table).filter(table.id.in_(ids)).all()

def update_data(db: Session, table: Table, id: int, data: BaseModel):
    db_data = db.query(table).filter(table.id == id).first()
    if db_data is None:
        return None
    for key, value in data.dict().items():
        setattr(db_data, key, value)
    db.commit()
    db.refresh(db_data)
    return db_data


def delete_data(db: Session, table: Table, id: int):
    db_data = db.query(table).filter(table.id == id).first()
    if db_data is None:
        return None
    db.delete(db_data)
    db.commit()
    return {"message": f"Instance of {table.__name__} deleted successfully"}

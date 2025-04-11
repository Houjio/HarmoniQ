from sqlalchemy import Table
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from harmoniq.db.engine import sql_tables
from harmoniq.db import schemas


async def read_all_data(db: Session, table: Table):
    return db.query(table).all()


async def create_data(db: Session, table: Table, data: BaseModel):
    db_data = table(**data.dict())
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    return db_data


async def read_data_by_id(db: Session, table: Table, id: int):
    return db.query(table).filter(table.id == id).first()


async def read_multiple_by_id(db: Session, table: Table, ids: List[int]):
    return db.query(table).filter(table.id.in_(ids)).all()


async def update_data(db: Session, table: Table, id: int, data: BaseModel):
    db_data = db.query(table).filter(table.id == id).first()
    if db_data is None:
        return None
    for key, value in data.dict().items():
        setattr(db_data, key, value)
    db.commit()
    db.refresh(db_data)
    return db_data


async def delete_data(db: Session, table: Table, id: int):
    db_data = db.query(table).filter(table.id == id).first()
    if db_data is None:
        return None
    db.delete(db_data)
    db.commit()
    return {"message": f"Instance of {table.__name__} deleted successfully"}

# Async fixers

async def read_all_bus_async(db: Session):
    return await read_all_data(db, schemas.Bus)

async def read_all_line_async(db: Session):
    return await read_all_data(db, schemas.Line)

async def read_all_line_type_async(db: Session):
    return await read_all_data(db, schemas.LineType)

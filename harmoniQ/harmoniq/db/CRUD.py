from sqlalchemy import Table
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from harmoniq.db.engine import sql_tables
from harmoniq.db import schemas

# CRUD.py : Ce fichier contient des fonctions utilitaires pour effectuer des opérations CRUD (Create, Read, Update, Delete) sur les tables SQLAlchemy.
# Ces fonctions sont conçues pour être génériques et peuvent être utilisées pour n'importe quelle table de la base de données.
# They are designed to be generic and can be used for any table in the database.


async def read_all_data(db: Session, table: Table):
    return db.query(table).all()


async def create_data(db: Session, table: Table, data: BaseModel):
    db_data = table(**data.dict())
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    return db_data


# This function is used to read data from the database by its ID, reads everything.
async def read_data_by_id(db: Session, table: Table, id: int):
    return db.query(table).filter(table.id == id).first()

# This function is used to read multiple data from the database by their IDs.
async def read_multiple_by_id(db: Session, table: Table, ids: List[int]):
    return db.query(table).filter(table.id.in_(ids)).all()

# This function is used to update data in the database by its ID.
async def update_data(db: Session, table: Table, id: int, data: BaseModel):
    db_data = db.query(table).filter(table.id == id).first()
    if db_data is None:
        return None
    for key, value in data.dict().items():
        setattr(db_data, key, value)
    db.commit()
    db.refresh(db_data)
    return db_data

# This function is used to delete data from the database by its ID.
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


"""
EXAMPLE: (All of that is done in the js file)

@app.put("/buses/{bus_id}",response_model=schemas.BusResponse,summary="Update a bus’s properties")

async def update_bus(
bus_id: int,
bus_in: schemas.BusCreate,            # Pydantic model for incoming data
db: Session = Depends(get_db)         # our session generator
):
# Call the generic updater:
updated: schemas.Bus = await update_data(db, schemas.Bus, bus_id, bus_in)

if not updated:
    raise HTTPException(status_code=404, detail="Bus not found")

# FastAPI will use BusResponse to serialize ORM → JSON
return updated
"""
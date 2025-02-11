from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from harmoniq.db import shemas
from harmoniq.db import engine
from harmoniq.db.engine import get_db
# from harmoniq.core import meteo
# from harmoniq.core.meteo import Granularity

router = APIRouter(
    prefix="/api",
    tags=["api"],
    responses={404: {"description": "Not found"}},
)


@router.get("/ping")
async def ping():
    return {"ping": "pong"}


@router.post("/eoliennes/", response_model=shemas.EolienneResponse)
def create_eolienne_endpoint(eolienne: shemas.EolienneCreate, db: Session = Depends(get_db)):
    result = engine.create_eolienne(db, eolienne)
    if result is None:
        raise HTTPException(status_code=404, detail="Eolienne not found")
    return result

@router.get("/eoliennes/", response_model=List[shemas.EolienneResponse])
def read_eoliennes_endpoint(db: Session = Depends(get_db)):
    result = engine.read_eoliennes(db)
    return result

@router.get("/eoliennes/{eolienne_id}", response_model=shemas.EolienneResponse)
def read_eolienne_endpoint(eolienne_id: int, db: Session = Depends(get_db)):
    result = engine.read_eolienne(db, eolienne_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Eolienne {eolienne_id} not found")
    return result

@router.put("/eoliennes/{eolienne_id}", response_model=shemas.EolienneResponse)
def update_eolienne_endpoint(eolienne_id: int, eolienne: shemas.EolienneCreate, db: Session = Depends(get_db)):
    result = engine.update_eolienne(db, eolienne_id, eolienne)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Eolienne {eolienne_id} not found")
    return result

@router.delete("/eoliennes/{eolienne_id}")
def delete_eolienne_endpoint(eolienne_id: int, db: Session = Depends(get_db)):
    result = engine.delete_eolienne(db, eolienne_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Eolienne {eolienne_id} not found")
    
    return result

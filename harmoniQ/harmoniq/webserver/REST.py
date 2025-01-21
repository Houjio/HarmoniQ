from fastapi import APIRouter, Depends, HTTPException
from harmoniq.db import shemas
from sqlalchemy.orm import Session
from typing import List

from harmoniq.db import engine

router = APIRouter(
    prefix="/api",
    tags=["api"],
    responses={404: {"description": "Not found"}},
)


@router.get("/ping")
async def ping():
    return {"ping": "pong"}


@router.post("/stations", response_model=shemas.StationMeteoRead)
def cree_station_meteo(
    station: shemas.StationMeteoCreate, db: Session = Depends(engine.get_db)
):
    return engine.create_station(station, db)


@router.get("/stations", response_model=List[shemas.StationMeteoRead])
def recupere_chaque_station(db: Session = Depends(engine.get_db)):
    return engine.get_all_stations(db)


@router.get("/stations/{station_id}", response_model=shemas.StationMeteoRead)
def recupere_station_avec_id(station_id: int, db: Session = Depends(engine.get_db)):
    station = engine.get_station_by_id(station_id, db)
    if station is None:
        raise HTTPException(status_code=404, detail="Station non trouvée")
    return station


@router.get("/stations/iata/{iata_id}", response_model=shemas.StationMeteoRead)
def recupere_station_avec_iata_id(iata_id: str, db: Session = Depends(engine.get_db)):
    station = engine.get_station_by_iata_id(iata_id, db)
    if station is None:
        raise HTTPException(status_code=404, detail="Station non trouvée")
    return station


@router.delete("/stations/{station_id}")
def suprimer_station(station_id: int, db: Session = Depends(engine.get_db)):
    station = engine.get_station_by_id(station_id, db)
    if station is None:
        raise HTTPException(status_code=404, detail="Station non trouvée")
    engine.delete_station(station_id, db)
    return {"message": "Station supprimée"}


@router.post("/stations/n_proches")
def recupere_stations_proches(
    latitude: float, longitude: float, n: int, db: Session = Depends(engine.get_db)
):
    stations = engine.get_n_nearest_stations(
        latitude=latitude, longitude=longitude, n=n, db=db
    )
    return stations

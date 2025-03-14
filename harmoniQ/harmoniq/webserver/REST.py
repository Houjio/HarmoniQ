from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from harmoniq.db import shemas
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from harmoniq.db import shemas
from harmoniq.core import meteo
from harmoniq.db import engine
from harmoniq.core.meteo import Granularity
from harmoniq.db.engine import get_db

router = APIRouter(
    prefix="/api",
    tags=["api"],
    responses={404: {"description": "Not found"}},
)


@router.get("/ping")
async def ping():
    return {"ping": "pong"}


@router.post("/meteo/get_data")
def get_meteo_data(
    latitude: float,
    longitude: float,
    interpolate: bool,
    start_time: datetime,
    granularity: int,
    end_time: Optional[datetime] = None,
):
    try:
        granularity = Granularity(granularity)
    except ValueError:
        raise HTTPException(status_code=400, detail="Granularity must be 1 or 2")

    helper = meteo.WeatherHelper(
        position=shemas.PositionBase(latitude=latitude, longitude=longitude),
        interpolate=interpolate,
        start_time=start_time,
        end_time=end_time,
        granularity=granularity,
    )
    helper.load()
    csv_buffer = helper.data.to_csv()
    return StreamingResponse(
        csv_buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=weather_data.csv"},
    )


@router.post("/eoliennes/", response_model=shemas.EolienneResponse)
def create_eolienne_endpoint(
    eolienne: shemas.EolienneCreate, db: Session = Depends(get_db)
):
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
def update_eolienne_endpoint(
    eolienne_id: int, eolienne: shemas.EolienneCreate, db: Session = Depends(get_db)
):
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


@router.post("/eolienne_parcs/", response_model=shemas.EolienneParcResponse)
def create_eolienne_parc_endpoint(
    eolienne_parc: shemas.EolienneParcCreate, db: Session = Depends(get_db)
):
    result = engine.create_eolienne_parc(db, eolienne_parc)
    if result is None:
        raise HTTPException(status_code=404, detail="Eolienne Parc not found")
    return result


@router.get("/eolienne_parcs/", response_model=List[shemas.EolienneParcResponse])
def read_eolienne_parcs_endpoint(db: Session = Depends(get_db)):
    result = engine.read_eolienne_parcs(db)
    return result


@router.get(
    "/eolienne_parcs/{eolienne_parc_id}", response_model=shemas.EolienneParcResponse
)
def read_eolienne_parc_endpoint(eolienne_parc_id: int, db: Session = Depends(get_db)):
    result = engine.read_eolienne_parc(db, eolienne_parc_id)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"Eolienne Parc {eolienne_parc_id} not found"
        )
    return result


@router.put(
    "/eolienne_parcs/{eolienne_parc_id}", response_model=shemas.EolienneParcResponse
)
def update_eolienne_parc_endpoint(
    eolienne_parc_id: int,
    eolienne_parc: shemas.EolienneParcCreate,
    db: Session = Depends(get_db),
):
    result = engine.update_eolienne_parc(db, eolienne_parc_id, eolienne_parc)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"Eolienne Parc {eolienne_parc_id} not found"
        )
    return result


@router.delete("/eolienne_parcs/{eolienne_parc_id}")
def delete_eolienne_parc_endpoint(eolienne_parc_id: int, db: Session = Depends(get_db)):
    result = engine.delete_eolienne_parc(db, eolienne_parc_id)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"Eolienne Parc {eolienne_parc_id} not found"
        )

    return result


@router.get(
    "/eolienne_parcs/{eolienne_parc_id}/eoliennes",
    response_model=List[shemas.EolienneResponse],
)
def read_eoliennes_in_parc_endpoint(
    eolienne_parc_id: int, db: Session = Depends(get_db)
):
    result = engine.all_eoliennes_in_parc(db, eolienne_parc_id)
    return result


@router.post("/meteo/get_data")
def get_meteo_data(
    latitude: float,
    longitude: float,
    interpolate: bool,
    start_time: datetime,
    granularity: int,
    end_time: Optional[datetime] = None,
):
    try:
        granularity = Granularity(granularity)
    except ValueError:
        raise HTTPException(status_code=400, detail="Granularity must be 1 or 2")

    helper = meteo.WeatherHelper(
        position=shemas.PositionBase(latitude=latitude, longitude=longitude),
        interpolate=interpolate,
        start_time=start_time,
        end_time=end_time,
        granularity=granularity,
    )
    helper.load()
    csv_buffer = helper.data.to_csv()
    return StreamingResponse(
        csv_buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=weather_data.csv"},
    )

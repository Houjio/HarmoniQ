from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import logging
from typing import List, Optional
from datetime import datetime
import pandas as pd

from harmoniq.db import schemas, engine, CRUD
from harmoniq.db.CRUD import (
    create_data,
    read_all_data,
    read_data_by_id,
    update_data,
    delete_data,
)
from harmoniq.core import meteo
from harmoniq.db.engine import get_db

from harmoniq.modules.eolienne import InfraParcEolienne

router = APIRouter(
    prefix="/api",
    responses={404: {"description": "Not found"}},
)


@router.get("/ping")
async def ping():
    return {"ping": "pong"}


# Initialisation des fonctions CRUD des tables de la base de données
api_routers = {}
for sql_class, pydantic_classes in engine.sql_tables.items():
    table_name = sql_class.__name__
    table_name_lower = table_name.lower()
    table_name_plural = table_name_lower + "s"
    table_cap_plural = table_name + "s"

    base_class = pydantic_classes["base"]
    create_class = pydantic_classes["create"]
    response_class = pydantic_classes["response"]

    class_router = APIRouter(
        prefix=f"/{table_name_lower}",
        tags=[table_name],
        responses={404: {"description": f"{table_name} not found"}},
    )
    api_routers[table_name_lower] = class_router

    # Define the endpoints within a closure
    def create_endpoints(
        sql_class, base_class, create_class, response_class, table_name_lower
    ):
        @class_router.post("/", response_model=response_class)
        async def create(item: create_class, db: Session = Depends(get_db)):
            result = create_data(db, sql_class, item)
            if result is None:
                raise HTTPException(
                    status_code=404, detail=f"{table_name_lower} not found"
                )
            return result

        @class_router.get("/", response_model=List[response_class])
        async def read_all(db: Session = Depends(get_db)):
            result = read_all_data(db, sql_class)
            return result

        @class_router.get("/{item_id}", response_model=response_class)
        async def read(item_id: int, db: Session = Depends(get_db)):
            result = read_data_by_id(db, sql_class, item_id)
            if result is None:
                raise HTTPException(
                    status_code=404, detail=f"{table_name_lower} {item_id} not found"
                )
            return result

        @class_router.put("/{item_id}", response_model=response_class)
        async def update(
            item_id: int, item: create_class, db: Session = Depends(get_db)
        ):
            result = update_data(db, sql_class, item_id, item)
            if result is None:
                raise HTTPException(
                    status_code=404, detail=f"{table_name_lower} {item_id} not found"
                )
            return result

        @class_router.delete("/{item_id}")
        async def delete(item_id: int, db: Session = Depends(get_db)):
            result = delete_data(db, sql_class, item_id)
            if result is None:
                raise HTTPException(
                    status_code=404, detail=f"{table_name_lower} {item_id} not found"
                )
            return result

    # Call the closure to define the endpoints
    create_endpoints(
        sql_class, base_class, create_class, response_class, table_name_lower
    )


# Éolienne
eolienne_router = api_routers.get("eolienne")
if eolienne_router is None:
    raise Exception("Eolienne router not found")


@eolienne_router.get("/parc/{eolienne_parc_id}")
async def read_eoliennes_in_parc(eolienne_parc_id: int, db: Session = Depends(get_db)):
    result = engine.all_eoliennes_in_parc(db, eolienne_parc_id)
    return result


# Meteo
meteo_router = APIRouter(
    prefix="/meteo",
    tags=["Meteo"],
    responses={404: {"description": "Not found"}},
)


@meteo_router.post("/get_data")
def get_meteo_data(
    latitude: float,
    longitude: float,
    interpolate: bool,
    start_time: datetime,
    granularity: int,
    end_time: Optional[datetime] = None,
):
    try:
        granularity = meteo.Granularity(granularity)
    except ValueError:
        raise HTTPException(status_code=400, detail="Granularity must be 1 or 2")

    helper = meteo.WeatherHelper(
        position=schemas.PositionBase(latitude=latitude, longitude=longitude),
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


router.include_router(meteo_router)

# Parc éolien
parc_eolien_router = api_routers['eolienneparc']

@parc_eolien_router.post("/{parc_eolien_id}/production")
def calculer_production_parc_eolien(parc_eolien_id: int, scenario_id: int, db: Session = Depends(get_db)):
    list_eolienne = engine.all_eoliennes_in_parc(db, parc_eolien_id)
    scenario = CRUD.read_scenario_by_id(db, scenario_id)
    if list_eolienne is None:
        raise HTTPException(status_code=404, detail="Parc éolien not found")
    
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    eolienne_infra = InfraParcEolienne(list_eolienne)
    eolienne_infra.charger_scenario(scenario)
    production:pd.DataFrame = eolienne_infra.calculer_production()

    json_prod = production.to_json()

    return json_prod


# Ajout des routes aux endpoint
for _, api_router in api_routers.items():
    router.include_router(api_router)

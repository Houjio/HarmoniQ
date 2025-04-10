import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from typing import List, Optional
from datetime import datetime
import pandas as pd
import time

from harmoniq.db import schemas, engine, CRUD
from harmoniq.db.CRUD import (
    create_data,
    read_all_data,
    read_multiple_by_id,
    read_data_by_id,
    update_data,
    delete_data,
)
from harmoniq.db.demande import read_demande_data, read_demande_data_sankey
from harmoniq.core import meteo
from harmoniq.db.engine import get_db
from harmoniq.core.fausse_données import production_aleatoire

from harmoniq.modules.eolienne import InfraParcEolienne

router = APIRouter(
    prefix="/api",
    responses={404: {"description": "Not found"}},
)


@router.get("/ping")
async def ping():
    return {"ping": "pong"}


@router.post("/simulation")
async def simulation(
    scenario_id: int, liste_infra_id: int, db: Session = Depends(get_db)
):
    print(f"Scenario ID: {scenario_id}")
    print(f"Infrastructure ID: {liste_infra_id}")
    scenario = CRUD.read_scenario_by_id(db, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    infra = CRUD.read_liste_infrastructures_by_id(db, liste_infra_id)
    if infra is None:
        raise HTTPException(status_code=404, detail="Infrastructure not found")

    print("Scenario:")
    print(scenario)
    print("Infra:")
    print(infra)

    raise HTTPException(status_code=501, detail="Simulation not implemented")


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
    )
    api_routers[table_name_lower] = class_router

    # Define the endpoints within a closure
    def create_endpoints(
        sql_class, base_class, create_class, response_class, table_name_lower
    ):
        @class_router.post(
            "/", response_model=response_class, summary=f"Create a {table_name}"
        )
        async def create(item: create_class, db: Session = Depends(get_db)):
            result = await create_data(db, sql_class, item)
            if result is None:
                raise HTTPException(
                    status_code=404, detail=f"{table_name_lower} not found"
                )
            return result

        @class_router.get(
            "/",
            response_model=List[response_class],
            summary=f"Read all {table_name_plural}",
        )
        async def read_all(db: Session = Depends(get_db)):
            result = await read_all_data(db, sql_class)
            return result

        @class_router.get(
            "/multiple/{ids}",
            response_model=List[response_class],
            summary=f"Read multiple {table_name_plural} by id",
        )
        async def read_multiple(ids: str, db: Session = Depends(get_db)):
            id_list = [int(i) for i in ids.split(",")]
            result = await read_multiple_by_id(db, sql_class, id_list)
            if len(result) != len(id_list):
                missing_ids = set(id_list) - {item.id for item in result}
                raise HTTPException(
                    status_code=200,
                    detail=f"The following IDs were not found: {', '.join(map(str, missing_ids))}",
                )
            return result

        @class_router.get(
            "/{item_id}",
            response_model=response_class,
            summary=f"Read a {table_name} by id",
        )
        async def read(item_id: int, db: Session = Depends(get_db)):
            result = await read_data_by_id(db, sql_class, item_id)
            if result is None:
                raise HTTPException(
                    status_code=404, detail=f"{table_name_lower} {item_id} not found"
                )
            return result

        @class_router.put(
            "/{item_id}",
            response_model=response_class,
            summary=f"Update a {table_name} by id",
        )
        async def update(
            item_id: int, item: create_class, db: Session = Depends(get_db)
        ):
            result = await update_data(db, sql_class, item_id, item)
            if result is None:
                raise HTTPException(
                    status_code=404, detail=f"{table_name_lower} {item_id} not found"
                )
            return result

        @class_router.delete("/{item_id}", summary=f"Delete a {table_name} by id")
        async def delete(item_id: int, db: Session = Depends(get_db)):
            result = await delete_data(db, sql_class, item_id)
            if result is None:
                raise HTTPException(
                    status_code=404, detail=f"{table_name_lower} {item_id} not found"
                )
            return result

    # Call the closure to define the endpoints
    create_endpoints(
        sql_class, base_class, create_class, response_class, table_name_lower
    )

# Demande
demande_router = APIRouter(
    prefix="/demande",
    tags=["Demande"],
    responses={404: {"description": "Not found"}},
)


@demande_router.post("/")
async def read_demande(
    scenario_id: int,
    CUID: Optional[int] = None,
    db: Session = Depends(get_db),
):
    scenario = await read_data_by_id(db, schemas.Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    demande = await read_demande_data(scenario, CUID)
    return demande


@demande_router.post("/sankey")
async def read_demande_sankey(
    scenario_id: int,
    CUID: Optional[int] = None,
    db: Session = Depends(get_db),
):
    scenario = await read_data_by_id(db, schemas.Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    demande = await read_demande_data_sankey(scenario, CUID)
    return demande


router.include_router(demande_router)

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
parc_eolien_router = api_routers["eolienneparc"]


@parc_eolien_router.post("/{parc_eolien_id}/production")
async def calculer_production_parc_eolien(
    parc_eolien_id: int, scenario_id: int, db: Session = Depends(get_db)
):
    eolienne_parc_task = read_data_by_id(db, schemas.EolienneParc, parc_eolien_id)
    scenario_task = read_data_by_id(db, schemas.Scenario, scenario_id)

    eolienne_parc, scenario = await asyncio.gather(eolienne_parc_task, scenario_task)
    if eolienne_parc is None:
        raise HTTPException(status_code=404, detail="Parc éolien not found")

    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    eolienne_infra = InfraParcEolienne(eolienne_parc)
    await eolienne_infra.charger_scenario(scenario)
    production: pd.DataFrame = eolienne_infra.calculer_production()

    return production


# Fausses données
faker_router = APIRouter(
    prefix="/faker",
    tags=["Faker"],
    responses={404: {"description": "Not found"}},
)


@faker_router.post("/production")
async def get_production_aleatoire(scenario_id: int, db: Session = Depends(get_db)):
    scenario = await read_data_by_id(db, schemas.Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=200, detail="Scenario not found")

    production = await asyncio.to_thread(production_aleatoire, scenario)
    return production


router.include_router(faker_router)


# Ajout des routes aux endpoint
for _, api_router in api_routers.items():
    router.include_router(api_router)

# Demand data: either from demande.db (read-only) or synthetic (duck curve + seasonal).
# Mode: set HARMONIQ_DEMANDE_MODE to "db" | "synthetic" | leave unset (auto: db if file exists else synthetic).

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from harmoniq import DEMANDE_PATH
from harmoniq.db.schemas import Consomation, Scenario, Weather
from harmoniq.db.synthetic_demande import (
    generate_synthetic_demande_data,
    generate_synthetic_sankey,
    generate_synthetic_temporal,
)

_DEMANDE_MODE = os.environ.get("HARMONIQ_DEMANDE_MODE", "").strip().lower()
_DB_EXISTS = Path(DEMANDE_PATH).exists()

if _DEMANDE_MODE == "db":
    _use_synthetic = False
    if not _DB_EXISTS:
        raise FileNotFoundError(
            f"HARMONIQ_DEMANDE_MODE=db but demande.db not found at {DEMANDE_PATH}. "
            "Place the file or use --demande-synthetic / HARMONIQ_DEMANDE_MODE=synthetic."
        )
elif _DEMANDE_MODE == "synthetic":
    _use_synthetic = True
else:
    # auto: use DB if present, else synthetic
    _use_synthetic = not _DB_EXISTS

_conn = None
if not _use_synthetic:
    import sqlite3
    _conn = sqlite3.connect(f"file:{DEMANDE_PATH}?mode=ro", uri=True)


def _weather_str(scenario: Scenario):
    w = getattr(scenario, "weather", None)
    return Weather(w).name if w is not None else Weather.typical.name


def _consomation_str(scenario: Scenario):
    c = getattr(scenario, "consomation", None)
    return Consomation(c).name if c is not None else Consomation.PV.name


async def get_all_sectors() -> pd.DataFrame:
    if _use_synthetic:
        return pd.DataFrame({"sector": ["Résidentiel", "Commercial", "Industriel", "Transport", "Autre"]})
    query = """
        SELECT DISTINCT m.sector
        FROM Metadata m
        JOIN Demande d ON d.meta_id = m.id
    """
    return pd.read_sql_query(query, _conn)


async def read_demande_data(
    scenario: Scenario,
    CUID: Optional[int] = None,
) -> pd.DataFrame:
    if _use_synthetic:
        return generate_synthetic_demande_data(scenario, CUID)

    query = """
        SELECT d.date, d.electricity, d.gaz, m.sector
        FROM Demande d
        JOIN Metadata m ON d.meta_id = m.id
        WHERE m.CUID = ?
        AND m.weather = ?
        AND m.scenario = ?
        AND d.date BETWEEN ? AND ?
    """
    params = (
        CUID or 1,
        _weather_str(scenario),
        _consomation_str(scenario),
        scenario.date_de_debut,
        scenario.date_de_fin,
    )
    return pd.read_sql_query(query, _conn, params=params)


async def read_demande_data_sankey(
    scenario: Scenario,
    CUID: Optional[int] = None,
) -> pd.DataFrame:
    if _use_synthetic:
        return generate_synthetic_sankey(scenario, CUID)

    query = """
        SELECT m.sector, SUM(d.electricity) AS total_electricity, SUM(d.gaz) AS total_gaz
        FROM Demande d
        JOIN Metadata m ON d.meta_id = m.id
        WHERE m.CUID = ?
        AND m.weather = ?
        AND m.scenario = ?
        AND d.date BETWEEN ? AND ?
        GROUP BY m.sector
    """
    params = (
        CUID or 1,
        _weather_str(scenario),
        _consomation_str(scenario),
        scenario.date_de_debut,
        scenario.date_de_fin,
    )
    return pd.read_sql_query(query, _conn, params=params)


async def read_demande_data_temporal(
    scenario: Scenario,
    CUID: Optional[int] = None,
) -> pd.DataFrame:
    if _use_synthetic:
        return generate_synthetic_temporal(scenario, CUID)

    query = """
        SELECT d.date, SUM(d.electricity) AS total_electricity, SUM(d.gaz) AS total_gaz
        FROM Demande d
        JOIN Metadata m ON d.meta_id = m.id
        WHERE m.CUID = ?
        AND m.weather = ?
        AND m.scenario = ?
        AND d.date BETWEEN ? AND ?
        GROUP BY d.date
    """
    params = (
        CUID or 1,
        _weather_str(scenario),
        _consomation_str(scenario),
        scenario.date_de_debut,
        scenario.date_de_fin,
    )
    df = pd.read_sql_query(query, _conn, params=params)
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    return df


if __name__ == "__main__":
    import asyncio
    from datetime import timedelta
    from types import SimpleNamespace
    scenario = SimpleNamespace(
        date_de_debut=datetime(2035, 1, 1),
        date_de_fin=datetime(2035, 1, 31),
        pas_de_temps=timedelta(hours=1),
    )
    df = asyncio.run(read_demande_data_temporal(scenario, CUID=None))
    print(df.head())

# Seperate database since it is read only

from harmoniq import DEMANDE_PATH
from harmoniq.db.schemas import Scenario, Weather, Consomation

import pandas as pd
import sqlite3

from typing import Optional

_conn = sqlite3.connect(f"file:{DEMANDE_PATH}?mode=ro", uri=True)


async def get_all_sectors() -> pd.DataFrame:
    query = """
        SELECT DISTINCT m.sector
        FROM Metadata m
        JOIN Demande d ON d.meta_id = m.id
    """
    df = pd.read_sql_query(query, _conn)
    return df

async def read_demande_data(
    scenario: Scenario,
    CUID: Optional[int] = None,
) -> pd.DataFrame:
    if CUID is None:
        CUID = 1  # Default value = Total

    query = """
        SELECT d.date, d.electricity, d.gaz, m.sector
        FROM Demande d
        JOIN Metadata m ON d.meta_id = m.id
        WHERE m.CUID = ?
        AND m.weather = ?
        AND m.scenario = ?
        AND d.date BETWEEN ? AND ?
    """

    weather_string = Weather(scenario.weather).name
    consomation_string = Consomation(scenario.consomation).name

    params = (
        CUID,
        weather_string,
        consomation_string,
        scenario.date_de_debut,
        scenario.date_de_fin,
    )
    df = pd.read_sql_query(query, _conn, params=params)
    return df


async def read_demande_data_sankey(
    scenario: Scenario,
    CUID: Optional[int] = None,
) -> pd.DataFrame:
    if CUID is None:
        CUID = 1  # Default value = Total

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

    weather_string = Weather(scenario.weather).name
    consomation_string = Consomation(scenario.consomation).name

    params = (
        CUID,
        weather_string,
        consomation_string,
        scenario.date_de_debut,
        scenario.date_de_fin,
    )
    df = pd.read_sql_query(query, _conn, params=params)
    return df


async def read_demande_data_temporal(
    scenario: Scenario,
    CUID: Optional[int] = None,
) -> pd.DataFrame:
    if CUID is None:
        CUID = 1  # Default value = Total

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
    weather_string = Weather(scenario.weather).name
    consomation_string = Consomation(scenario.consomation).name
    params = (
        CUID,
        weather_string,
        consomation_string,
        scenario.date_de_debut,
        scenario.date_de_fin,
    )
    df = pd.read_sql_query(query, _conn, params=params)
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    return df


if __name__ == "__main__":
    # Test the function
    import asyncio
    scenario = Scenario(
        weather=1,
        consomation=1,
        date_de_debut="2035-01-01",
        date_de_fin="2035-01-31",
    )
    df = asyncio.run(read_demande_data(scenario, CUID=2431))
    print(df)

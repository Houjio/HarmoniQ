# Seperate database since it is read only

from harmoniq import DEMANDE_PATH
from harmoniq.db.schemas import Scenario, Weather, Consomation

import pandas as pd
import sqlite3

from typing import Optional

_conn = sqlite3.connect(f"file:{DEMANDE_PATH}?mode=ro", uri=True)

def get_all_mrc() -> pd.DataFrame:
    query = """
        SELECT DISTINCT m.id, m.CUID, m.weather, m.sector, m.scenario, m.year
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
        CUID = 1 # Default value = Total

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


if __name__ == "__main__":
    # Test the function
    scenario = Scenario(
        weather=1,
        consomation=1,
        date_de_debut="2035-01-01",
        date_de_fin="2035-01-31",
    )
    df = read_demande_data(scenario, CUID=2431)
    print(df)
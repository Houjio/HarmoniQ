import numpy as np
import pandas as pd
import datetime

from harmoniq.db.schemas import ScenarioBase, InfrastructureBase


def scenario_to_range(
    scenario: ScenarioBase,
) -> pd.DatetimeIndex:
    """
    Convert a scenario to a date range.
    """
    start: datetime.datetime = scenario.date_de_debut
    end: datetime.datetime = scenario.date_de_fin
    timestep: datetime.timedelta = scenario.pas_de_temps

    time_range = pd.date_range(start=start, end=end, freq=timestep)

    return time_range

def production_aleatoire(scenario: ScenarioBase) -> pd.DataFrame:
    """
    Generate random production data for a given scenario.
    """
    time_range = scenario_to_range(scenario)

    production = (
        100 * np.sin(2 * np.pi * (time_range.hour - 6) / 24) ** 2
        + 50 * np.sin(2 * np.pi * (time_range.hour - 18) / 24) ** 2
        + 20
        + np.random.normal(0, 5, len(time_range))
    )

    production_df = pd.DataFrame({"temps": time_range, "production": production})

    return production_df

def production_infra(
        scenario: ScenarioBase,
        infra: InfrastructureBase,
) -> pd.DataFrame:
    """
    Generate random production data for a given infrastructure and scenario.
    """
    time_range = scenario_to_range(scenario)

    production = (
        100 * np.sin(2 * np.pi * (time_range.hour - 6) / 24) ** 2
        + 50 * np.sin(2 * np.pi * (time_range.hour - 18) / 24) ** 2
        + 20
        + np.random.normal(0, 5, len(time_range))
    )

    production_df = pd.DataFrame({"temps": time_range, "production": production})

    return production_df
import numpy as np
import pandas as pd
import datetime

from harmoniq.db.schemas import ScenarioBase


def production_aleatoire(scenario: ScenarioBase) -> pd.DataFrame:
    start: datetime.datetime = scenario.date_de_debut
    end: datetime.datetime = scenario.date_de_fin
    timestep: datetime.timedelta = scenario.pas_de_temps

    time_range = pd.date_range(start=start, end=end, freq=timestep)

    production = (
        100 * np.sin(2 * np.pi * (time_range.hour - 6) / 24) ** 2
        + 50 * np.sin(2 * np.pi * (time_range.hour - 18) / 24) ** 2
        + 20
        + np.random.normal(0, 5, len(time_range))
    )

    production_df = pd.DataFrame({"temps": time_range, "production": production})

    return production_df

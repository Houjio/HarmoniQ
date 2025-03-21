from harmoniq.core.base import Infrastructure, necessite_scenario
from harmoniq.core.meteo import WeatherHelper, Granularity, EnergyType
from harmoniq.db.schemas import ScenarioBase, SolaireBase, PositionBase
from harmoniq.modules.solaire.calculs_production_solaire import *

from typing import List
import pandas as pd
import logging

logger = logging.getLogger("Solaire")

class InfraParcSolaire(Infrastructure):
    def __init__(self, donnees: List[SolaireBase]):
        super().__init__(donnees)

    def _charger_meteo(self, scenario: ScenarioBase):

        pos = PositionBase(
            latitude=solaire.latitude, longitude=solaire.latitude # COMMENT import ?
        )
        granularite = (
            Granularity.HOURLY if scenario.pas_de_temps.days == 0 else Granularity.DAILY
        )
        logger.info(f"Granularité de Meteo: {granularite}")
        
        solar_energy = EnergyType.SOLAIRE

        helper = WeatherHelper(
            position=pos,
            start_time=scenario.date_de_debut,
            end_time=scenario.date_de_fin,
            interpolate=True,
            granularity=granularite,
            data_type=solar_energy,
        )

        return helper.load()

    def charger_scenario(self, scenario):
        self.scenario: ScenarioBase = scenario
        self.meteo: pd.DataFrame = self._charger_meteo(scenario)


    @necessite_scenario
    def calculer_production(self) -> pd.DataFrame:
        # TODO: Ce code repete souvent les memes calcules, il faudrait le refactoriser

        new_df = None

        keys = []

        for eolienne in self.donnees:
            nom = eolienne.eolienne_nom
            keys.append(nom)

            logger.info(f"Calcul de la production pour {nom}")
            turbine_data = get_turbine_power(eolienne, self.meteo)

            # Replace puissance with the name of the turbine
            turbine_data = turbine_data.rename(columns={"puissance": nom})

            turbine_data.rename(columns={"puissance": nom}, inplace=True)
            if new_df is None:
                new_df = turbine_data
            else:
                new_df[nom] = turbine_data[nom]

        new_df["production"] = new_df[keys].sum(axis=1)

        return new_df


if __name__ == "__main__":
    from harmoniq.db.CRUD import read_all_solaire_parc, read_all_scenario
    from harmoniq.db.engine import get_db
    from datetime import datetime, timedelta

    db = next(get_db())
    eolienne_parc = read_all_eolienne_parc(db)[0]
    eoliennes = all_eoliennes_in_parc(db, eolienne_parc.id)
    infraEolienne = InfraParcEolienne(eoliennes)

    scenario = read_all_scenario(db)[0]

    infraEolienne.charger_scenario(scenario)

    production = infraEolienne.calculer_production()

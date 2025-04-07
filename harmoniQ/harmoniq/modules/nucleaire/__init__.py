from harmoniq.core.base import Infrastructure, necessite_scenario
from harmoniq.core.meteo import WeatherHelper, Granularity, EnergyType
from harmoniq.db.schemas import NucleaireBase, ScenarioBase, PositionBase
from harmoniq.modules.nucleaire.calculs_production_nucleaire import (
    calculate_nuclear_production,
)

from typing import List
import pandas as pd
import logging

logger = logging.getLogger("Solaire")


class Nucleaire(Infrastructure):
    def __init__(self, donnees: List[NucleaireBase]):

        super().__init__(donnees)
        self.donnees = donnees

    def _charger_meteo(self, scenario: ScenarioBase):
        nucleaire = self.donnes
        pos = PositionBase(latitude=nucleaire.latitude, longitude=nucleaire.latitude)
        granularite = (
            Granularity.HOURLY if scenario.pas_de_temps.days == 0 else Granularity.DAILY
        )
        logger.info(f"Granularité de Meteo: {granularite}")

        nuclear_energy = EnergyType.NUCLEAIRE
        helper = WeatherHelper(
            position=pos,
            start_time=scenario.date_de_debut,
            end_time=scenario.date_de_fin,
            interpolate=True,
            granularity=granularite,
            data_type=nuclear_energy,
        )

        return helper.load()

    @necessite_scenario
    def charger_scenario(self, scenario: ScenarioBase):
        self.scenario: ScenarioBase = scenario
        self.meteo: pd.DataFrame = self._charger_meteo(scenario)

    @necessite_scenario
    def calculer_production(self) -> pd.DataFrame:
        new_df = None

        keys = []

        for centrale in self.donnees:
            nom = centrale.centrale_nom
            keys.append(nom)

            logger.info(f"Calcul de la production pour {nom}")
            centrale_data = calculate_nuclear_production(centrale, self.meteo)
            if new_df is None:
                new_df = centrale_data
            else:
                new_df = pd.concat([new_df, centrale_data], axis=1)
        return new_df


if __name__ == "__main__":
    from harmoniq.db.CRUD import read_all_centrales_nucleaires, read_all_scenario
    from harmoniq.db.engine import get_db, all_eoliennes_in_parc
    from datetime import datetime, timedelta

    db = next(get_db())
    centrale = read_all_centrales_nucleaires(db, centrale_id=1)
    infraNucleaire = Nucleaire(centrale)

    scenario = read_all_scenario(db)[0]

    infraNucleaire.charger_scenario(scenario)

    production = infraNucleaire.calculer_production()

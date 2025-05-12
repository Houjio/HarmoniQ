from harmoniq.core.base import Infrastructure, necessite_scenario
from harmoniq.core.meteo import WeatherHelper, Granularity, EnergyType
from harmoniq.db.schemas import ScenarioBase, EolienneParcBase, PositionBase
from harmoniq.modules.eolienne.calcule import get_parc_power
import datetime

from typing import List
import pandas as pd
import logging

logger = logging.getLogger("EolienneParc")


class InfraParcEolienne(Infrastructure):
    def __init__(self, donnees: EolienneParcBase):
        super().__init__(donnees)

    def _charger_meteo(self, scenario: ScenarioBase):
        lat = self.donnees.latitude
        long = self.donnees.longitude
        logger.info(f"Latitude: {lat}, Longitude: {long}")
        pos = PositionBase(latitude=lat, longitude=long)
        granularite = (
            Granularity.HOURLY if scenario.pas_de_temps.days == 0 else Granularity.DAILY
        )
        logger.info(f"Granularité de Meteo: {granularite}")

        wind_energy = EnergyType.EOLIEN

        helper = WeatherHelper(
            position=pos,
            interpolate=True,
            start_time=scenario.date_de_debut,
            end_time=scenario.date_de_fin,
            data_type=wind_energy,
            granularity=granularite,
        )


        return helper.load()

    async def charger_scenario(self, scenario):
        self.scenario: ScenarioBase = scenario
        self.meteo: pd.DataFrame = self._charger_meteo(scenario)

    @necessite_scenario
    def calculer_production(self) -> pd.DataFrame:
        nom = self.donnees.nom
        logger.info(f"Calcul de la production pour {nom}")
        parc_data = get_parc_power(self.donnees, self.meteo)
        print(parc_data)
        return parc_data


if __name__ == "__main__":
    from harmoniq.db.CRUD import read_all_scenario, read_all_eolienne_parc
    import asyncio
    from harmoniq.db.engine import get_db

    db = next(get_db())
    production_totale = pd.DataFrame()
    for parc in read_all_eolienne_parc(db):
        parc_id = parc.id
        print(f"Traitement du parc éolien avec l'ID: {parc_id}")
        eolienne_parc = read_all_eolienne_parc(db)[parc_id - 1]
        infraEolienne = InfraParcEolienne(eolienne_parc)

        scenario = read_all_scenario(db)[0]

        asyncio.run(infraEolienne.charger_scenario(scenario))

        production_iteration = infraEolienne.calculer_production()
        if parc_id == 1:
            production_totale = production_iteration
        else:
            production_totale["puissance"] += production_iteration["puissance"]
        break
    prod_totale = production_totale["puissance"].sum() / 1000  # Convertir en MW
    print(f"Production totale: {prod_totale} MW")



from harmoniq.core.base import Infrastructure, necessite_cas
from harmoniq.core.meteo import WeatherHelper, Granularity, EnergyType
from harmoniq.db.schemas import CasBase, Eolienne, PositionBase
from harmoniq.modules.eolienne.calcule import get_turbine_power

import pandas as pd


class InfraEolienne(Infrastructure):
    def __init__(self, donnees):
        super().__init__(donnees)

    def _charger_meteo(self, cas: CasBase):
        pos = PositionBase(
            latitude=self.donnees.latitude, longitude=self.donnees.longitude
        )
        granularite = (
            Granularity.HOURLY if cas.pas_de_temps.days == 0 else Granularity.DAILY
        )
        wind_energy = EnergyType.EOLIEN

        helper = WeatherHelper(
            position=pos,
            start_time=cas.date_de_debut,
            end_time=cas.date_de_fin,
            interpolate=True,
            granularity=granularite,
            data_type=wind_energy,
        )

        return helper.load()

    def charger_cas(self, cas):
        self.cas: CasBase = cas
        self.meteo: pd.DataFrame = self._charger_meteo(cas)

    @necessite_cas
    def calculer_production(self):
        return get_turbine_power(self.donnees, self.meteo)


if __name__ == "__main__":
    from harmoniq.db.CRUD import read_all_eolienne
    from harmoniq.db.engine import get_db
    from datetime import datetime, timedelta

    db = next(get_db())
    eolienne = read_all_eolienne(db)[0]
    infraEolienne = InfraEolienne(eolienne)

    cas = CasBase(
        nom="Test",
        date_de_debut=datetime(2021, 1, 1),
        date_de_fin=datetime(2021, 1, 2),
        pas_de_temps=timedelta(hours=1),
    )

    infraEolienne.charger_cas(cas)

    production = infraEolienne.calculer_production()

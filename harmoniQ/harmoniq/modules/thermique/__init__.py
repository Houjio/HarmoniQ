from harmoniq.core.base import Infrastructure, necessite_scenario
from harmoniq.db.schemas import ThermiqueBase, ScenarioBase
from harmoniq.modules.thermique.calculs_production_thermique import (
    calculate_thermique_production,
)

import pandas as pd
import logging

logger = logging.getLogger("Thermique")


class Thermique(Infrastructure):
    def __init__(self, donnees: ThermiqueBase):

        super().__init__(donnees)
        self.donnees:ThermiqueBase = donnees
        self.production: pd.DataFrame = None

    def charger_scenario(self, scenario: ScenarioBase):
        self.scenario: ScenarioBase = scenario
        self.production = None

    @necessite_scenario
    def calculer_production(self) -> pd.DataFrame:
        if self.production is not None:
            return self.production

        nom = self.donnees.nom
        logger.info(f"Calcul de la production pour {nom}")


        self.production = calculate_thermique_production(
            power_mw=self.donnees.puissance_nominal,
            maintenance_week=self.donnees.semaine_maintenance,
            date_start=self.scenario.date_de_debut,
            date_end=self.scenario.date_de_fin,
        )
        return self.production



if __name__ == "__main__":
    from harmoniq.db.CRUD import read_all_thermique, read_all_scenario
    from harmoniq.db.engine import get_db

    db = next(get_db())
    centrale = read_all_thermique(db)[0]
    infraThermique = Thermique(centrale)

    scenario = read_all_scenario(db)[0]

    infraThermique.charger_scenario(scenario)

    production = infraThermique.calculer_production()

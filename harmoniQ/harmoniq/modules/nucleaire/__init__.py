from harmoniq.core.base import Infrastructure, necessite_scenario
from harmoniq.db.schemas import NucleaireBase, ScenarioBase
from harmoniq.modules.nucleaire.calculs_production_nucleaire import (
    calculate_nuclear_production,
)

import pandas as pd
import logging

logger = logging.getLogger("Nucleaire")


class Nucleaire(Infrastructure):
    def __init__(self, donnees: NucleaireBase):

        super().__init__(donnees)
        self.donnees:NucleaireBase = donnees
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


        self.production = calculate_nuclear_production(
            power_mw=self.donnees.puissance_nominal,
            maintenance_week=self.donnees.semaine_maintenance,
            date_start=self.scenario.date_de_debut,
            date_end=self.scenario.date_de_fin,
        )
        return self.production



if __name__ == "__main__":
    from harmoniq.db.CRUD import read_all_nucleaire, read_all_scenario
    from harmoniq.db.engine import get_db

    db = next(get_db())
    centrale = read_all_nucleaire(db)[0]
    infraNucleaire = Nucleaire(centrale)

    scenario = read_all_scenario(db)[0]

    infraNucleaire.charger_scenario(scenario)

    production = infraNucleaire.calculer_production()

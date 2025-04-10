from harmoniq.core.base import Infrastructure, necessite_scenario
from harmoniq.db.schemas import ScenarioBase, SolaireBase
from harmoniq.modules.solaire.calculs_production_solaire import (
    calculate_energy_solar_plants,
    calculate_regional_residential_solar,
    calculate_installation_cost,
    co2_emissions_solar,
    cost_solar_powerplant,
    calculate_lifetime,
)


from typing import List
import pandas as pd
import logging

logger = logging.getLogger("Solaire")


class Solaire(Infrastructure):
    def __init__(self, donnees: SolaireBase):

        super().__init__(donnees)
        self.donnees:SolaireBase = donnees
        self.production: pd.DataFrame = None

    def charger_scenario(self, scenario):
        self.scenario: ScenarioBase = scenario
        self.production = None

    @necessite_scenario
    def calculer_production(self) -> pd.DataFrame:
        if self.production is not None:
            return self.production
        
        nom = self.donnees.nom
        logger.info(f"Calcul de la production pour {nom}")

        self.production = calculate_energy_solar_plants(
            latitude=self.donnees.latitude,
            longitude=self.donnees.longitude,
            angle_panneau=self.donnees.angle_panneau,
            orientation_panneau=self.donnees.orientation_panneau,
            puissance_nominal=self.donnees.puissance_nominal,
            nombre_panneau=self.donnees.nombre_panneau,
            date_start=self.scenario.date_de_debut,
            date_end=self.scenario.date_de_fin,
        )
        return self.production


if __name__ == "__main__":
    from harmoniq.db.CRUD import read_all_solaire, read_all_scenario
    from harmoniq.db.engine import get_db

    db = next(get_db())
    centrale = read_all_solaire(db)[0]
    infraSolaire = Solaire(centrale)

    scenario = read_all_scenario(db)[0]

    infraSolaire.charger_scenario(scenario)

    production = infraSolaire.calculer_production()

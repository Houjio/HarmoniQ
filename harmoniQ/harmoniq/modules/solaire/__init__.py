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


class InfraParcSolaire(Infrastructure):
    def __init__(self, donnees: SolaireBase):
        super().__init__(donnees)


    def charger_scenario(self, scenario):
        self.scenario: ScenarioBase = scenario

    @necessite_scenario
    def calculer_production(self) -> pd.DataFrame:
        _, resultats_df = calculate_energy_solar_plants(self.donnees)

        return resultats_df

    def calculer_cout_construction(self) -> float:
        """Calculer le coût de construction de la centrale solaire"""
        return cost_solar_powerplant(self.donnees)

    def calculer_co2_eq_construction(self) -> float:
        """Calculer les émissions de CO2 équivalentes de la construction"""
        return co2_emissions_solar(self.donnees)


if __name__ == "__main__":
    from harmoniq.db.CRUD import read_all_solaire, read_all_scenario
    from harmoniq.db.engine import get_db

    db = next(get_db())
    # Récupérer la première centrale solaire
    centrale_solaire = read_all_solaire(db)[0]
    infraSolaire = InfraParcSolaire(centrale_solaire)

    # Charger le scénario
    scenario = read_all_scenario(db)[0]
    infraSolaire.charger_scenario(scenario)
    production = infraSolaire.calculer_production()

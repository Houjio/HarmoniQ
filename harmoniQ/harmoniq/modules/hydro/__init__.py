from harmoniq.core.base import Infrastructure, necessite_scenario
from harmoniq.db.schemas import HydroBase, ScenarioBase

from typing import List



class Hydro(Infrastructure):

    def __init__(self, donnees: List[HydroBase]):
        super().__init__(donnees)

    @necessite_scenario
    def _charger_debit(self,scenario):

        pass

    def _charger_scenario(self):
        # Ajouter un debit pour
        scenario: ScenarioBase = self.scenario

        date_debut = scenario.date_de_debut
        date_fin = scenario.date_fin

        return

    




    pass

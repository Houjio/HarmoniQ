from harmoniq.core.base import Infrastructure, necessite_scenario
from harmoniq.db.schemas import NucleaireBase, ScenarioBase
from typing import List


class Thermique(Infrastructure):

    def __init__(self, donnees: List[NucleaireBase]):
     
        super().__init__(donnees)
        self.donnees = donnees

    @necessite_scenario
    def charger_centrale(self, scenario: ScenarioBase):
    
        return self.donnees
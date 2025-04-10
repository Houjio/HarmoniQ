from harmoniq.core.base import Infrastructure, necessite_scenario
from harmoniq.db.schemas import ThermiqueBase, ScenarioBase
from typing import List

from typing import List


class Thermique(Infrastructure):

    def __init__(self, donnees: List[ThermiqueBase]):

        super().__init__(donnees)
        self.donnees = donnees

    @necessite_scenario
    def charger_centrale(self, scenario: ScenarioBase):

        return self.donnees

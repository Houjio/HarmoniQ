from harmoniq.core.base import Infrastructure
from harmoniq.db.schemas import HydroBase, ScenarioBase

from typing import List

class Hydro(Infrastructure):

    def __init__(self, donnees: List[HydroBase]):
        super().__init__(donnees)

    def _charger_debit(self, debit: ScenarioBase):à
        # Ajouter un debit pour 
    pass

from harmoniq.db.schemas import ScenarioBase, BaseModel

import numpy as np


def necessite_scenario(func):
    def wrapper(*args, **kwargs):
        if not args[0].scenario_charger:
            raise ValueError("Scenario pas charger")
        return func(*args, **kwargs)

    return wrapper


class Infrastructure:
    def __init__(self, donnees: BaseModel):
        self.donnees = donnees
        self.scenario = None

    def __repr__(self):
        return f"<Infrastructure {self.donnees.nom} de type {self.donnees.type}>"

    def charger_scenario(self, scenario: ScenarioBase) -> None:
        self.scenario = scenario

    @property
    def scenario_charger(self) -> bool:
        return self.scenario is not None

    @necessite_scenario
    def calculer_production(self) -> np.ndarray:
        """Placeholder pour le calcul de la production"""
        raise NotImplementedError

    @necessite_scenario
    def calculer_cout_construction(self) -> np.ndarray:
        """Placeholder pour le calcul du coût de construction"""
        raise NotImplementedError

    @necessite_scenario
    def calculer_cout_pas_de_temps(self) -> np.ndarray:
        """Placeholder pour le calcul du coût par pas de temps"""
        raise NotImplementedError

    def calculer_co2_eq_construction(self) -> np.ndarray:
        """Placeholder pour le calcul des émissions de CO2 équivalentes de la construction"""
        raise NotImplementedError

    def calculer_co2_eq_pas_de_temps(self) -> np.ndarray:
        """Placeholder pour le calcul des émissions de CO2 équivalentes du fonctionnement"""
        raise NotImplementedError

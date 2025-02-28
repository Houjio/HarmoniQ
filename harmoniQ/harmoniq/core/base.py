from harmoniq.db.schemas import InfrastructureBase, CasBase

import numpy as np


def necessite_cas(func):
    def wrapper(*args, **kwargs):
        if not args[0].cas_charger:
            raise ValueError("Cas pas charger")
        return func(*args, **kwargs)

    return wrapper


class Infrastructure:
    def __init__(self, donnees: InfrastructureBase):
        self.donnees = donnees
        self.cas = None

    def __repr__(self):
        return f"<Infrastructure {self.donnees.nom} de type {self.donnees.type}>"

    def charger_cas(self, cas: CasBase) -> None:
        self.cas = cas

    @property
    def cas_charger(self) -> bool:
        return self.cas is not None

    @necessite_cas
    def calculer_production(self) -> np.ndarray:
        """Placeholder pour le calcul de la production"""
        return

    @necessite_cas
    def calculer_cout_construction(self) -> np.ndarray:
        """Placeholder pour le calcul du coût de construction"""
        return

    @necessite_cas
    def calculer_cout_pas_de_temps(self) -> np.ndarray:
        """Placeholder pour le calcul du coût par pas de temps"""
        return

    def calculer_co2_eq_construction(self) -> np.ndarray:
        """Placeholder pour le calcul des émissions de CO2 équivalentes de la construction"""
        return

    def calculer_co2_eq_pas_de_temps(self) -> np.ndarray:
        """Placeholder pour le calcul des émissions de CO2 équivalentes du fonctionnement"""
        return

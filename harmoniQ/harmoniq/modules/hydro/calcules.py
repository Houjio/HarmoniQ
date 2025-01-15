import numpy as np
import pandas as pd

from dataclasses import dataclass


@dataclass
class Hydro:
    nom: str
    production_par_heure_kw: float

    def production_par_temps(self, heures: int) -> float:
        return self.production_par_heure_kw * heures


if __name__ == "__main__":
    print("Lancement de calcules hydro")
    print("Création d'une instance de Hydro")
    a = Hydro("Beaurnois", 1_000_000)
    print(a)
    print("Calcule pour 5 heures")
    t = a.production_par_temps(5)
    print(f"Production pour 5 heures: {t}")
    print("Fin de calcules hydro")

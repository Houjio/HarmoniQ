# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 11:34:19 2025

@author: Admin
"""

import numpy as np

def estimer_qualite_ecosysteme_futur(facteur_charge):
    """
    Estime l'impact futur sur la qualité des écosystèmes en fonction du facteur de charge d'un nouveau barrage hydroélectrique.
    :param facteur_charge: Facteur de charge du nouveau barrage (valeur entre 0 et 1).
    :return: Estimation de l'impact futur sur la qualité des écosystèmes (PDF*m²*yr/kWh).
    """
    # Pourcentages de l'hydroélectricité dans chaque région
    mix_energie_hydro = {
        "Hydro-Québec": 97.6,
        "Vermont": 16.88,
        "Maine": 25.87,
        "New York": 18.16,
        "Connecticut": 0.86,
        "New Hampshire": 6.69,
        "Massachusetts": 2.52,
        "Rhode Island": 0.05,
    }

    # Qualité des écosystèmes total observé (extrait de la Figure 2)
    qualite_ecosysteme_total = {
        "Hydro-Québec": 17,
        "Vermont": 37,
        "Maine": 396,
        "New York": 389,
        "Connecticut": 388,
        "New Hampshire": 387,
        "Massachusetts": 612,
        "Rhode Island": 735,
    }

    # Transformation des données pour résoudre le système d'équations
    A = []
    B = []

    for region, mix in mix_energie_hydro.items():
        A.append([mix / 100])  # Conversion en proportion
        B.append(qualite_ecosysteme_total[region])

    # Conversion en matrices numpy
    A = np.array(A)
    B = np.array(B)

    # Résolution du système A * X = B pour trouver l'impact de l'hydroélectricité
    X = np.linalg.lstsq(A, B, rcond=None)[0]

    # Production actuelle et future (en % du mix énergétique du Québec)
    production_actuelle = mix_energie_hydro["Hydro-Québec"] / 100
    production_future = production_actuelle + facteur_charge * (1 - production_actuelle)

    # Estimation de l'impact futur sur la qualité des écosystèmes
    qualite_ecosysteme_futur = X[0] * production_future

    return qualite_ecosysteme_futur

# Exemple d'utilisation
facteur_charge_input = 0.55  # Exemple : Facteur de charge du nouveau barrage
resultat_qualite_ecosysteme_futur = estimer_qualite_ecosysteme_futur(facteur_charge_input)
print(f"Estimation de l'impact futur sur la qualité des écosystèmes (2023-2050) : {resultat_qualite_ecosysteme_futur:.2f} PDF*m²*yr/kWh")

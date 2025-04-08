import numpy as np

def estimer_daly_futur(facteur_charge):
    """
    Estime le DALY futur en fonction du facteur de charge d'un nouveau barrage hydroélectrique.
    :param facteur_charge: Facteur de charge du nouveau barrage (valeur entre 0 et 1).
    :return: Estimation du DALY futur (DALY/kWh).
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

    # DALY total observé (extrait de la Figure 2)
    daly_total = {
        "Hydro-Québec": 1e-7,
        "Vermont": 5e-7,
        "Maine": 15e-7,
        "New York": 16e-7,
        "Connecticut": 16e-7,
        "New Hampshire": 17e-7,
        "Massachusetts": 24e-7,
        "Rhode Island": 27e-7,
    }

    # Transformation des données pour résoudre le système d'équations
    A = []
    B = []

    for region, mix in mix_energie_hydro.items():
        A.append([mix / 100])  # Conversion en proportion
        B.append(daly_total[region])

    # Conversion en matrices numpy
    A = np.array(A)
    B = np.array(B)

    # Résolution du système A * X = B pour trouver le DALY de l'hydroélectricité
    X = np.linalg.lstsq(A, B, rcond=None)[0]

    # Production actuelle et future (en % du mix énergétique du Québec)
    production_actuelle = mix_energie_hydro["Hydro-Québec"] / 100
    production_future = production_actuelle + facteur_charge * (1 - production_actuelle)

    # Estimation du DALY futur
    daly_futur = X[0] * production_future

    return daly_futur

# Exemple d'utilisation
facteur_charge_input = 0.55  # Exemple : Facteur de charge du nouveau barrage
resultat_daly_futur = estimer_daly_futur(facteur_charge_input)
print(f"Estimation du DALY futur (2023-2050) : {resultat_daly_futur:.2e} DALY/kWh")

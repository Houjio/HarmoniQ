import pandas as pd
import matplotlib.pyplot as plt

def calculer_emissions_et_ressources(barrages):
    # Mise à jour des facteurs d'émission
    FACTEUR_EMISSION = {
        "fil de l'eau": 6,    # g éq CO2/kWh
        "réservoir": 17       # g éq CO2/kWh
    }
    
    # Mise à jour des ressources minérales et énergies non renouvelables
    UTILISATION_MINERALES = {
        "fil de l'eau": 0.019,  # mg Sb eq/kWh
        "réservoir": 0.019
    }
    
    UTILISATION_NON_RENOUVELABLES = {
        "fil de l'eau": 0.03,   # MJ/kWh
        "réservoir": 0.03
    }

    # Valeurs de référence des ressources minérales déjà définies
    UTILISATION_FIL_EAU = 0.001  # kg indisponible/kWh pour hydro fil de l'eau
    UTILISATION_RESERVOIR = 0.0005  # kg indisponible/kWh pour hydro réservoir
    EXTRACTION_MINERALE = 0.031  # mg Sb/kWh pour l'extraction
    
    resultats = []
    
    for barrage in barrages:
        nom = barrage["nom"]
        energie_theorique = max(barrage["energie_theorique"], 1)  # éviter division par zéro
        energie_reelle = barrage["energie_reelle"]
        type_barrage = barrage["type"]
        
        # Calcul du facteur de charge
        facteur_de_charge = energie_reelle / energie_theorique
        
        # Sélection des bons facteurs
        facteur_emission = FACTEUR_EMISSION.get(type_barrage, 0)
        energie_minerale = UTILISATION_MINERALES.get(type_barrage, 0)
        energie_non_renouvelable = UTILISATION_NON_RENOUVELABLES.get(type_barrage, 0)
        
        # Calcul des émissions de CO2
        emissions = facteur_de_charge * energie_reelle * facteur_emission  # en grammes de CO2
        emissions_tonnes = emissions / 1e6  # conversion en tonnes
        
        # Calcul de l'utilisation des ressources minérales (en tonnes)
        ressources_minerales_utilisation = (
            facteur_de_charge * energie_reelle * (UTILISATION_FIL_EAU if type_barrage == "fil de l'eau" else UTILISATION_RESERVOIR)
        )
        
        # Calcul de l'extraction des ressources minérales (en kg Sb)
        ressources_minerales_extraction = facteur_de_charge * energie_reelle * (EXTRACTION_MINERALE / 1e6)
        
        # Calcul de l'utilisation des énergies minérales (en kg Sb)
        utilisation_energie_minerale = facteur_de_charge * energie_reelle * (energie_minerale / 1e3)  # conversion mg -> kg
        
        # Calcul de l'utilisation des énergies non renouvelables (en GJ)
        utilisation_energie_non_renouvelable = facteur_de_charge * energie_reelle * (energie_non_renouvelable / 1e3)  # conversion MJ -> GJ
        
        resultats.append({
            "Barrage": nom,
            "Facteur de charge": round(facteur_de_charge, 3),
            "Émissions (tonnes CO2/an)": round(emissions_tonnes, 2),
            "Utilisation ressources minérales (tonnes/an)": round(ressources_minerales_utilisation, 6),
            "Extraction ressources minérales (kg Sb/an)": round(ressources_minerales_extraction, 6),
            "Utilisation des énergies minérales (kg Sb/an)": round(utilisation_energie_minerale, 6),
            "Utilisation des énergies non renouvelables (GJ/an)": round(utilisation_energie_non_renouvelable, 6)
        })
    
    return pd.DataFrame(resultats)

def afficher_resultats(barrages):
    df_resultats = calculer_emissions_et_ressources(barrages)

    # Affichage dans la console
    print("\nEstimations des émissions et des ressources minérales:")
    print(df_resultats.to_string(index=False))

    # Graphique des émissions de CO2
    plt.figure(figsize=(8, 5))
    plt.bar(df_resultats["Barrage"], df_resultats["Émissions (tonnes CO2/an)"], color='blue', alpha=0.7)
    plt.xlabel("Barrages")
    plt.ylabel("Émissions (tonnes CO2/an)")
    plt.title("Émissions annuelles de CO2 par barrage")
    plt.xticks(rotation=30)
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.show()

    # Graphique de l'utilisation des énergies non renouvelables
    plt.figure(figsize=(8, 5))
    plt.bar(df_resultats["Barrage"], df_resultats["Utilisation des énergies non renouvelables (GJ/an)"], color='orange', alpha=0.7)
    plt.xlabel("Barrages")
    plt.ylabel("Utilisation des énergies non renouvelables (GJ/an)")
    plt.title("Consommation d'énergies non renouvelables par barrage")
    plt.xticks(rotation=30)
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.show()

# Exemple d'entrée
barrages = [
    {"nom": "Barrage A", "energie_theorique": 1000000000, "energie_reelle": 750000000, "type": "réservoir"},
    {"nom": "Barrage B", "energie_theorique": 2000000000, "energie_reelle": 1800000000, "type": "fil de l'eau"}
]

# Affichage des résultats
afficher_resultats(barrages)

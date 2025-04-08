import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

def interpoler_cout_barrage(puissance_demande):
    # Données
    puissance = np.array([10, 100, 1000, 10000, 100000, 1000000])  # Puissance du barrage (MW)
    cout_total = np.array([31354284, 275089949, 2713345805, 27096335649, 2.70926E+11, 2.70923E+12])  # Coût total ($)
    
    # Création de la fonction d'interpolation cubique
    interpolation_fonction = interp1d(puissance, cout_total, kind='cubic', fill_value="extrapolate")
    
    # Calcul du coût interpolé
    cout_interpole = interpolation_fonction(puissance_demande)
    
    return cout_interpole

# Données pour le tracé
puissance = np.array([10, 100, 1000, 10000, 100000, 1000000])
cout_total = np.array([31354284, 275089949, 2713345805, 27096335649, 2.70926E+11, 2.70923E+12])

# Fonction d'estimation basée sur la régression log-log
def estimation_cout_barrage(puissance_demande):
    a, b = 0.9903508069996744, 14.917112141681883
    return np.exp(b) * puissance_demande**a

# Exemple d'utilisation
def main():
    puissance_demande = float(input("Entrez la puissance du barrage (MW) : "))
    cout_estime = estimation_cout_barrage(puissance_demande)
    print(f"Coût estimé pour un barrage de {puissance_demande} MW : {cout_estime:.2f} $")

if __name__ == "__main__":
    main()

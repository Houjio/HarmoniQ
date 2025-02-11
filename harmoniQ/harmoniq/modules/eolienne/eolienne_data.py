"""Première itération de calcul avec le module NREL-PySAM appliqué à
    l'énergie éolienne.
    
    date de création : 2025-01-17
    auteur(s) : Alec Mitchell, alec.mitchell@polymtl.ca
                (Entrer votre nom ici si vous collaborez à ce fichier .py)
    
    dernière modification : 2025-01-19 (Alec Mitchell)
    
"""

# ___ Importation des modules nécessaires ___ #
# Modules communs
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Modules spécifiques au modèle
from PySAM import Windpower as wp


""" Dans ce premier exemple, nous réalisons l'analyse d'une ferme éolienne. Je donne ici une courte description
    des paramètres utilisés pour cette première analyse. Pour plus de détails, veuillez consulter la documentation 
    du NREL-PySAM sur le modèle WindPower à l'adresse suivante: https://nrel-pysam.readthedocs.io/en/latest/modules/Windpower.html
    
    Pour aller chercher des informations supplémentaires sur les classes, paramètres et fonctions de PySAM, vous pouvez simplement
    lancer la commande help(wp) pour obtenir une liste des classes et fonctions disponibles dans le module WindPower.
    
    Pour démarrer un modèle, on doit tout d'abord initier ce dernier, soit en créant une entité vierge ou en utilisant un modèle
    par défaut. Dans le premier cas, on peut utiliser la commande wp.new(). Dans le second cas, on peut utiliser la commande
    wp.default("nom_du_modèle"). Les modèles par défaut disponibles sont les suivants:
    
        - "WindPowerAllEquity"
        - "WindPowerCommercial"
        - "WindPowerLCOECalculator"
        - "WindPowerLeveragedPartnership
        - "WindPowerMerchantPlant"
        - "WindPowerNone"
        - "WindPowerResidential"
        - "WindPowerSaleLeaseback"
        - "WindPowerSingleOwner"
        
    Pour visualiser clairement les caractéristiques de chacun des modèles par défaut, utilisez les deux lignes de codes suivantes
    et consultez les informations affichées dans la console:
    
        new_wp = wp.default("nom_du_modèle")
        print(new_wp.export())
    
    Dans ce premier exemple, la seconde étape importante est de déterminer le mode d'analyse
"""


# Initialisation d'un modèle test afin de démontrer les fonctionnalités de PySAM
model = wp.default("WindPowerMerchantPlant")
model.Resource.wind_resource_model_choice = 1
model.Resource.weibull_k_factor = 2.0
model.Resource.weibull_wind_speed = 8.5
model.execute()

print(model.Outputs.monthly_energy)

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
import logging

logger = logging.getLogger("EnergyUtils")

class EnergyUtils:
    """
    Classe utilitaire pour les calculs énergétiques du réseau électrique.
    
    Cette classe fournit des méthodes pour:
    - Estimer la production d'énergie
    - Gérer les niveaux de réservoir
    - Calculer les coûts basés sur les niveaux
    - Obtenir des données historiques
    """
    
    @staticmethod
    def obtenir_energie_historique(annee: str, donnees_historiques=None) -> float: 
        """
        Récupère l'énergie historique produite par Hydro-Québec.
        
        Args:
            annee: Année des données historiques
            donnees_historiques: Données historiques optionnelles
            
        Returns:
            Énergie historique en MWh
        """
        # Valeurs par défaut pour Hydro-Québec (basées sur des données publiques)
        energie_historique = {
            "2022": 210.8e6,  # 210.8 TWh en MWh
            "2023": 205.2e6,
            "2024": 208.0e6  # Estimation
        }
        
        if annee in energie_historique:
            return energie_historique[annee]
        else:
            # Valeur par défaut si l'année n'est pas disponible
            logger.warning(f"Données historiques pour {annee} non disponibles, utilisation de la moyenne")
            return sum(energie_historique.values()) / len(energie_historique)
    
    @staticmethod
    def identifier_nouvelles_centrales(reseau, donnees_historiques=None) -> List:
        """
        Identifie les nouvelles centrales ajoutées par l'utilisateur.
        
        Args:
            reseau: Réseau PyPSA
            donnees_historiques: Données historiques optionnelles
            
        Returns:
            Liste des nouvelles centrales
        """
        # Dans une implémentation complète, on comparerait avec une base historique
        # Pour cette version, on considère que toutes les centrales spécifiées sont nouvelles
        return []  # Simplifié pour l'instant
    
    @staticmethod
    def estimer_production_annuelle(centrale) -> float:
        """
        Estime la production annuelle d'une nouvelle centrale.
        
        Args:
            centrale: Générateur PyPSA
            
        Returns:
            Production annuelle estimée en MWh
        """
        # Facteurs de capacité typiques par type de centrale
        facteurs_capacite = {
            "hydro_fil": 0.5,        # 50% pour l'hydro au fil de l'eau
            "hydro_reservoir": 0.55, # 55% pour l'hydro avec réservoir
            "eolien": 0.35,          # 35% pour l'éolien
            "solaire": 0.18,         # 18% pour le solaire au Québec
            "thermique": 0.85,       # 85% pour le thermique
            "nucléaire": 0.90        # 90% pour le nucléaire
        }
        
        # Calcul de l'énergie annuelle estimée
        puissance_nominale = centrale.p_nom
        carrier = centrale.carrier
        facteur = facteurs_capacite.get(carrier, 0.5)  # 0.5 par défaut si carrier inconnu
        heures_annee = 8760
        
        return puissance_nominale * facteur * heures_annee
    
    @staticmethod
    def obtenir_bus_frontiere(reseau, type_bus: str) -> str:
        """
        Obtient le bus frontière pour les interconnexions.
        
        Args:
            reseau: Réseau PyPSA
            type_bus: Type de bus recherché
            
        Returns:
            Nom du bus frontalier
        """
        # Recherche un bus de type approprié pour l'interconnexion
        buses_interconnexion = reseau.buses[reseau.buses.type == "interconnexion"]
        
        if not buses_interconnexion.empty:
            return buses_interconnexion.index[0]
        
        # Fallback sur un bus de production si pas d'interconnexion explicite
        buses_production = reseau.buses[reseau.buses.type == "prod"]
        if not buses_production.empty:
            return buses_production.index[0]
        
        # En dernier recours, prendre le premier bus
        logger.warning("Aucun bus d'interconnexion trouvé, utilisation du premier bus disponible")
        return reseau.buses.index[0]
    
    @staticmethod
    def get_niveau_reservoir(generateur_index: str, heure) -> float:
        """
        Obtient l'apport hydrique pour un réservoir à une heure donnée.
        
        Args:
            generateur_index: Index du générateur
            heure: Heure considérée
            
        Returns:
            Apport hydrique normalisé (0-1)
        """
        # Simplifié : apport constant équilibré avec la production moyenne
        return 0.02  # 2% du volume du réservoir par heure (très simplifié)
    
    @staticmethod
    def calcul_cout_reservoir(niveau: float) -> float:
        """
        Calcule le coût marginal en fonction du niveau du réservoir.
        
        Args:
            niveau: Niveau du réservoir (0-1)
            
        Returns:
            Coût marginal
        """
        # Paramètres de configuration
        cout_minimum = 5     # Coût quand le réservoir est plein
        cout_maximum = 150   # Coût quand le réservoir est presque vide
        niveau_critique = 0.25  # Niveau en dessous duquel le coût augmente rapidement
        
        # Vérifier que le niveau est dans les limites
        niveau = max(0, min(1, niveau))
        
        # Relation exponentielle (augmentation rapide quand niveau est bas)
        if niveau < niveau_critique:
            # Croissance exponentielle en dessous du seuil critique
            facteur = (niveau_critique - niveau) / niveau_critique
            cout = cout_minimum + (cout_maximum - cout_minimum) * np.exp(3 * facteur)
        else:
            # Décroissance linéaire au-dessus du seuil critique
            facteur = (1 - niveau) / (1 - niveau_critique)
            cout = cout_minimum + (cout_maximum/4 - cout_minimum) * facteur
        
        return round(cout, 2)

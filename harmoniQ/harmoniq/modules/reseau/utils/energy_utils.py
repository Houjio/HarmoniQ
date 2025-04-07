import numpy as np
import pandas as pd
from typing import List, Dict, Optional
import logging
from harmoniq.db.engine import get_db
from harmoniq.db.CRUD import read_all_hydro
from harmoniq.modules.hydro.calcule import reservoir_infill
from pathlib import Path

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
        # Valeurs par défaut pour Hydro-Québec
        energie_historique = {
            "2022": 210.8e6,  # 210.8 TWh en MWh
            "2023": 205.2e6,
            "2024": 208.0e6 
        }
        
        if annee in energie_historique:
            return energie_historique[annee]
        else:
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
        # Facteurs de capacité par type de centrale
        facteurs_capacite = {
            "hydro_fil": 0.5,
            "hydro_reservoir": 0.55,
            "eolien": 0.35,
            "solaire": 0.18,
            "thermique": 0.85,
            "nucléaire": 0.90
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
            type_bus: Type de bus recherché (non utilisé pour le moment)
            
        Returns:
            Nom du bus frontalier
        """
        # Pour l'instant, on utilise uniquement le bus Stanstead comme frontière
        bus_interconnexion = "Stanstead"
        
        if bus_interconnexion in reseau.buses.index:
            return bus_interconnexion
        else:
            logger.warning(f"Bus {bus_interconnexion} non trouvé, utilisation du premier bus disponible")
            return reseau.buses.index[0]
    
    @staticmethod
    def get_niveau_reservoir(productions: pd.DataFrame, niveaux_actuels: dict, timestamp) -> pd.DataFrame:
        """
        Calcule les nouveaux niveaux de réservoir en fonction des productions et des apports naturels.
        
        Args:
            productions: DataFrame contenant les productions pour chaque réservoir
            niveaux_actuels: Dictionnaire ou DataFrame des niveaux actuels de chaque réservoir (0-1)
            timestamp: Horodatage actuel pour l'apport naturel (peut être horaire alors que les données sont journalières)
            
        Returns:
            DataFrame des nouveaux niveaux de réservoir (0-1)
        """
        db = next(get_db())
        barrages = read_all_hydro(db)
        
        CURRENT_DIR = Path(__file__).parent.parent.parent.parent / "modules" / "hydro"
        APPORT_DIR = CURRENT_DIR / "apport_naturel"
        
        # Extraire uniquement la date (sans l'heure)
        date_jour = pd.Timestamp(timestamp.date())
        
        apport_naturel = pd.DataFrame(index=[timestamp])
        
        for barrage in barrages:
            if barrage.type_barrage == "Reservoir" and barrage.nom in productions.columns:
                try:
                    id_hq = str(barrage.id_HQ)
                    nom_fichier = f"{id_hq}.csv"
                    fichier_apport = APPORT_DIR / nom_fichier
                    
                    if fichier_apport.exists():
                        data_apport = pd.read_csv(fichier_apport)
                        data_apport["time"] = pd.to_datetime(data_apport["time"])
                        
                        jour_exact = data_apport[data_apport["time"].dt.date == date_jour.date()]
                        
                        if not jour_exact.empty:
                            apport_naturel[barrage.nom] = jour_exact["streamflow"].values[0]
                        else:
                            data_apport["diff"] = abs(data_apport["time"] - date_jour)
                            jour_proche = data_apport.loc[data_apport["diff"].idxmin()]
                            logger.warning(f"Date exacte {date_jour.date()} non trouvée pour {barrage.nom}, utilisation de la date la plus proche: {jour_proche['time'].date()}")
                            apport_naturel[barrage.nom] = jour_proche["streamflow"]
                    else:
                        logger.warning(f"Fichier d'apport {nom_fichier} introuvable pour {barrage.nom}, utilisation de la valeur par défaut")
                        apport_naturel[barrage.nom] = 15 
                except Exception as e:
                    logger.error(f"Erreur lors du chargement des apports pour {barrage.nom}: {str(e)}")
                    apport_naturel[barrage.nom] = 15
        

        if isinstance(niveaux_actuels, dict):
            niveaux_actuels_df = pd.DataFrame([niveaux_actuels])
        else:
            niveaux_actuels_df = niveaux_actuels
        
        niveaux_reservoir_df = reservoir_infill(
            besoin_puissance=productions,
            pourcentage_reservoir=niveaux_actuels_df,
            apport_naturel=apport_naturel,
            timestamp=timestamp
        )
        
        return niveaux_reservoir_df
    
    @staticmethod
    def calcul_cout_reservoir(niveau: float) -> float:
        """
        Calcule le coût marginal en fonction du niveau du réservoir.
        
        Args:
            niveau: Niveau du réservoir (0-1)
            
        Returns:
            Coût marginal
        """
        cout_minimum = 5     # Coût quand le réservoir est plein
        cout_maximum = 150   # Coût quand le réservoir est presque vide
        niveau_critique = 0.25  # Niveau en dessous duquel le coût augmente rapidement
        
        niveau = max(0, min(1, niveau))
        
        if niveau < niveau_critique:
            # Croissance exponentielle en dessous du seuil critique
            facteur = (niveau_critique - niveau) / niveau_critique
            cout = cout_minimum + (cout_maximum - cout_minimum) * np.exp(3 * facteur)
        else:
            # Décroissance linéaire au-dessus du seuil critique
            facteur = (1 - niveau) / (1 - niveau_critique)
            cout = cout_minimum + (cout_maximum/4 - cout_minimum) * facteur
        
        return round(cout, 2)

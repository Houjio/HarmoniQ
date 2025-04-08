from harmoniq.core.base import Infrastructure, necessite_scenario
from harmoniq.db.schemas import ScenarioBase, Hydro, ListeInfrastructures
from harmoniq.db.CRUD import read_all_hydro, read_multiple_by_id
from harmoniq.db.engine import get_db
from harmoniq.modules.hydro.calcule import reservoir_infill

from core import NetworkBuilder, PowerFlowAnalyzer, NetworkOptimizer
from utils import EnergyUtils, DATA_DIR

import pandas as pd
import numpy as np
import pypsa
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path

logger = logging.getLogger("Reseau")

class InfraReseau(Infrastructure):
    """
    Gestion du réseau électrique avec optimisation des imports/exports
    et pilotage adaptatif des réservoirs.
    
    Cette classe implémente le workflow complet du réseau électrique:
    1. Chargement et création du réseau
    2. Calcul de la capacité d'import/export
    3. Optimisation temporelle avec gestion des réservoirs
    4. Analyse des résultats
    
    Attributes:
        donnees: Liste des infrastructures du réseau
        scenario: Scénario de simulation
        network: Réseau PyPSA
        reservoir_levels: Niveaux des réservoirs
        statistics: Statistiques d'optimisation
    """
    
    def __init__(self, donnees: ListeInfrastructures, data_dir: str = None):
        """
        Initialise l'infrastructure réseau.
        
        Args:
            donnees: Liste des infrastructures incluses dans le réseau
            data_dir: Chemin vers le répertoire des données (optionnel)
        """
        super().__init__([donnees])
        self.network = None
        self.reservoir_levels = {}
        self.statistics = {}
        
        self.builder = NetworkBuilder(data_dir)
        
    def charger_scenario(self, scenario: ScenarioBase):
        """
        Charge le scénario de simulation.
        
        Args:
            scenario: Scénario à utiliser pour la simulation
        """
        self.scenario = scenario
        logger.info(f"Scénario chargé: {scenario.nom}")
        
    @necessite_scenario
    def creer_reseau(self, liste_infra=None) -> pypsa.Network:
        """
        Méthode principale de création du réseau électrique.
        
        Cette méthode crée un réseau PyPSA complet à partir des données statiques
        et des séries temporelles associées au scénario.
        
        Args:
            liste_infra: Liste des infrastructures à inclure dans le réseau (optionnel)
        
        Returns:
            pypsa.Network: Réseau prêt pour l'optimisation
        """
        from pathlib import Path
        import os
        import hashlib
        
        # Générer un identifiant unique pour cette configuration
        scenario_id = getattr(self.scenario, 'id', 0)
        scenario_name = getattr(self.scenario, 'nom', 'default').replace(' ', '_')
        scenario_date = getattr(self.scenario, 'date_de_debut', None)
        scenario_year = scenario_date.year if scenario_date else "unknown"
        
        # Créer une signature unique pour la liste d'infrastructures
        if liste_infra is None:
            liste_infra = self.donnees
            
        infra_id = getattr(liste_infra, 'id', 0)
        infra_hash = str(infra_id)
        try:
            # Tenter de créer un hash basé sur le contenu
            infra_str = str(liste_infra.dict()) if hasattr(liste_infra, 'dict') else str(infra_id)
            infra_hash = hashlib.md5(infra_str.encode()).hexdigest()[:8]
        except Exception:
            pass
        
        # Dossier pour le cache des réseaux
        module_dir = Path(__file__).parent
        cache_dir = module_dir / "network_cache"
        os.makedirs(cache_dir, exist_ok=True)
        
        # Nom du fichier de cache
        network_filename = f"network_s{scenario_id}_{scenario_year}_i{infra_id}_{infra_hash}.h5"
        network_path = cache_dir / network_filename
        
        # Vérifier si un réseau précalculé existe
        if network_path.exists():
            logger.info(f"Chargement du réseau précalculé depuis {network_path}")
            try:
                network = pypsa.Network()
                network.import_from_hdf5(str(network_path))
                
                # Vérification que le réseau est complet et valide
                if len(network.buses) == 0 or len(network.generators) == 0:
                    raise ValueError("Réseau incomplet")
                    
                self.network = network
                logger.info(f"Réseau chargé avec succès: {len(network.buses)} bus, " 
                        f"{len(network.lines)} lignes, {len(network.generators)} générateurs")
                return network
            except Exception as e:
                logger.warning(f"Erreur lors du chargement du réseau: {e}")
                # Supprimer le fichier cache corrompu
                try:
                    os.remove(network_path)
                    logger.info(f"Fichier cache supprimé: {network_path}")
                except:
                    pass
        
        # Création d'un nouveau réseau
        logger.info("Création d'un nouveau réseau électrique...")
        
        # Utiliser le builder pour créer le réseau
        annee = str(self.scenario.date_de_debut.year)
        start_date = self.scenario.date_de_debut
        end_date = self.scenario.date_de_fin
        
        network = self.builder.create_network(self.scenario, liste_infra, annee, start_date, end_date)
        
        # Normaliser les types de données avant sauvegarde
        self._normaliser_types_reseau(network)
        
        # Sauvegarder en format HDF5 (plus fiable que netCDF)
        try:
            logger.info(f"Sauvegarde du réseau vers {network_path}")
            network.export_to_hdf5(str(network_path))
            logger.info("Réseau sauvegardé avec succès")
        except Exception as e:
            logger.warning(f"Erreur lors de la sauvegarde du réseau: {e}")
        
        self.network = network
        
        logger.info(f"Réseau créé avec {len(network.buses)} bus, "
                    f"{len(network.lines)} lignes et "
                    f"{len(network.generators)} générateurs")
        
        return network

    def _normaliser_types_reseau(self, network):
        """
        Normalise les types de données dans le réseau pour éviter les erreurs lors de la sauvegarde.
        
        Args:
            network: Réseau PyPSA à normaliser
        """
        # Convertir le type de bus en chaîne de caractères
        if 'type' in network.buses.columns:
            network.buses.type = network.buses.type.astype(str)
        
        # Convertir d'autres colonnes problématiques si nécessaire
        for component in ['generators', 'loads', 'lines', 'transformers']:
            df = getattr(network, component)
            for col in df.columns:
                # Détecter et normaliser les colonnes avec types mixtes
                if df[col].dtype == 'object':
                    try:
                        # Tenter de convertir en chaîne pour les types mixtes
                        df[col] = df[col].astype(str)
                    except:
                        pass

    @necessite_scenario
    def calculer_capacite_import_export(self, liste_infra) -> float:
        """
        Phase 1: Calcul de la capacité d'import/export (Pmax)
        
        Cette méthode calcule la capacité maximale d'import/export en:
        1. Calculant le déséquilibre énergétique global (ΔE)
        2. Déterminant l'import théorique maximal à chaque heure
        3. Recherchant par dichotomie la valeur Pmax qui équilibre ΔE
        
        Returns:
            Capacité maximale d'import/export calculée (Pmax)
        """
        logger.info("Phase 1: Calcul de la capacité d'import/export...")
        
        if self.network is None:
            self.creer_reseau(liste_infra)
        
        annee = str(self.scenario.date_de_debut.year)
        
        energie_historique_HQ = EnergyUtils.obtenir_energie_historique(annee)
        besoins_totaux = self.network.loads_t.p_set.sum().sum()
        # Calcul du déséquilibre énergétique global (ΔE)
        deltaE = energie_historique_HQ - besoins_totaux
        
        # Ajustement pour les nouvelles centrales ajoutées
        nouvelles_centrales = EnergyUtils.identifier_nouvelles_centrales(self.network)
        for centrale in nouvelles_centrales:
            energie_estimee = EnergyUtils.estimer_production_annuelle(centrale)
            deltaE += energie_estimee
        
        # Calcul de l'import maximal théorique à chaque pas de temps
        import_max_theorique = []
        for heure in self.network.snapshots:
            try:
                # Besoins énergétiques - forcer la conversion en valeur scalaire
                besoins_df = self.network.loads_t.p_set.loc[heure]
                if isinstance(besoins_df, pd.Series):
                    besoins_heure = besoins_df.sum()
                else:
                    # Si c'est déjà un DataFrame, faire la somme totale
                    besoins_heure = besoins_df.sum().sum()
                    
                # Convertir en float seulement après avoir vérifié qu'on a bien un scalaire
                besoins_heure = float(besoins_heure)
                
                # Production maximale des sources fatales
                sources_fatales = self.network.generators[
                    self.network.generators.carrier.isin(['hydro_fil', 'eolien', 'solaire'])
                ].index
                
                # Calcul de la production fatale
                production_fatale = 0
                if not self.network.generators_t.p_max_pu.empty and len(sources_fatales) > 0:
                    for gen in sources_fatales:
                        if gen in self.network.generators_t.p_max_pu.columns:
                            p_nom = float(self.network.generators.loc[gen, 'p_nom'])
                            p_max_pu_val = float(self.network.generators_t.p_max_pu.loc[heure, gen])
                            
                            if pd.isna(p_nom) or pd.isna(p_max_pu_val):
                                logger.warning(f"Valeur NaN pour {gen}: p_nom={p_nom}, p_max_pu={p_max_pu_val}")
                                continue
                                
                            contribution = p_nom * p_max_pu_val
                            production_fatale += contribution
                
                # Calcul de l'import maximal
                import_max = besoins_heure - production_fatale
                import_max_theorique.append(import_max)
            
            except Exception as e:
                logger.error(f"Erreur lors du calcul pour {heure}: {str(e)}")
                # En cas d'erreur, ajouter une valeur par défaut
                import_max_theorique.append(0.0)
        
        # Recherche de Pmax pour équilibrer deltaE
        Pmax_min = min(import_max_theorique)  # Pourrait être négatif (export)
        Pmax_max = max(import_max_theorique)
        Pmax = (Pmax_min + Pmax_max) / 2
        
        tolerance = 0.1
        iterations_max = 100
        iteration = 0
        
        while iteration < iterations_max:
            # Calcul des imports/exports avec ce Pmax
            imports = [min(Pmax, max_theorique) for max_theorique in import_max_theorique]
            somme_imports = sum(imports)
            
            # Vérification de la convergence
            if abs(somme_imports - deltaE) < tolerance:
                break
            
            # Ajustement de Pmax
            if somme_imports > deltaE:
                Pmax_max = Pmax  # Trop d'import, réduire Pmax
            else:
                Pmax_min = Pmax  # Pas assez d'import, augmenter Pmax
            
            Pmax = (Pmax_min + Pmax_max) / 2
            iteration += 1
        
        logger.info(f"Pmax calculé: {Pmax:.2f} MW après {iteration} itérations")
        
        self.Pmax = Pmax
        self.deltaE = deltaE
        
        return Pmax

    @necessite_scenario
    def optimiser_avec_gestion_reservoirs(self, liste_infra, Pmax=None) -> pypsa.Network:
        """
        Phase 2: Optimisation avec gestion des réservoirs.
        
        Cette méthode effectue une optimisation du réseau avec:
        1. Importation/exportation selon Pmax
        2. Gestion dynamique des réservoirs d'eau
        3. Coûts marginaux variables selon les niveaux d'eau
        
        Args:
            liste_infra: Liste des infrastructures du réseau
            Pmax: Capacité maximale d'import/export (MW)
        
        Returns:
            pypsa.Network: Réseau optimisé
        """
        logger.info("Phase 2: Optimisation avec gestion des réservoirs...")
        
        if self.network is None:
            self.creer_reseau(liste_infra)
        
        if Pmax is None:
            if not hasattr(self, 'Pmax'):
                Pmax = self.calculer_capacite_import_export(liste_infra)
            else:
                Pmax = self.Pmax
        
        # Détermination du type d'échange (import ou export)
        bus_frontiere = EnergyUtils.obtenir_bus_frontiere(self.network, "Interconnexion")
        
        
        return self.network
    
    @necessite_scenario
    def workflow_import_export(self) -> Tuple[pypsa.Network, Dict]:
        """
        Exécute le workflow complet d'import/export avec gestion des réservoirs.
        
        Cette méthode combine les deux phases:
        1. Calcul de la capacité d'import/export
        2. Optimisation avec gestion adaptative des réservoirs
        
        Returns:
            Tuple contenant le réseau optimisé et les statistiques
        """
        logger.info("Démarrage du workflow d'optimisation avec gestion des imports/exports...")
        
        # Phase 1: Calcul de la capacité d'import/export
        Pmax = self.calculer_capacite_import_export()
        
        # Phase 2: Optimisation avec gestion des réservoirs
        network, statistics = self.optimiser_avec_gestion_reservoirs(Pmax)
        
        logger.info("Workflow d'optimisation terminé avec succès")
        return network, statistics
    
    @necessite_scenario
    def calculer_production(self) -> pd.DataFrame:
        """
        Calcule la production optimisée du réseau.
        
        Returns:
            DataFrame contenant la production par type d'énergie
        """
        if self.network is None or not self.statistics:
            self.workflow_import_export()
        
        # Agréger les données de production par type d'énergie
        if hasattr(self.network, 'generators_t') and hasattr(self.network.generators_t, 'p'):
            production = self.network.generators_t.p.copy()
            production['totale'] = production.sum(axis=1)
            
            carriers = self.network.generators.carrier.unique()
            for carrier in carriers:
                gens = self.network.generators[self.network.generators.carrier == carrier].index
                production[f'total_{carrier}'] = production[gens].sum(axis=1)
            
            return production
        else:
            logger.error("Aucune donnée de production disponible")
            return pd.DataFrame()

    def obtenir_statistiques(self) -> Dict:
        """
        Obtient les statistiques d'optimisation du réseau.
        
        Returns:
            Dict contenant les statistiques du réseau
        """
        if not self.statistics:
            logger.warning("Les statistiques ne sont pas disponibles, exécutez workflow_import_export d'abord")
            return {}
        
        return self.statistics

if __name__ == "__main__":
    from harmoniq.db.CRUD import read_data_by_id, read_all_scenario
    from harmoniq.db.engine import get_db
    from harmoniq.db.schemas import ListeInfrastructures
    import asyncio
    
    db = next(get_db())
    
    liste_infrastructures = asyncio.run(read_data_by_id(db, ListeInfrastructures, 2))
    infraReseau = InfraReseau(liste_infrastructures)
    
    scenario = read_all_scenario(db)[0]
    infraReseau.charger_scenario(scenario)

    # infraReseau.creer_reseau(liste_infrastructures)
    Pmax = infraReseau.calculer_capacite_import_export(liste_infrastructures)
    infraReseau.optimiser_avec_gestion_reservoirs(liste_infrastructures, Pmax)
    
    # network, statistics = infraReseau.workflow_import_export()
    # print(f"Capacité d'import/export (Pmax): {statistics['Pmax_calcule']:.2f} MW")
    # print(f"Énergie importée: {statistics['energie_importee']:.2f} MWh")
    # print(f"Énergie exportée: {statistics['energie_exportee']:.2f} MWh")
    
    # production = infraReseau.calculer_production()
    # print(f"Production totale: {production['totale'].sum():.2f} MWh")
    
    # print("\nProduction par type d'énergie:")
    # carriers = network.generators.carrier.unique()
    # for carrier in carriers:
    #     print(f"- {carrier}: {production[f'total_{carrier}'].sum():.2f} MWh")


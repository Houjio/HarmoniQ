from harmoniq.core.base import Infrastructure, necessite_scenario
from harmoniq.db.schemas import ScenarioBase, Hydro, ListeInfrastructures
from harmoniq.db.CRUD import read_all_hydro, read_multiple_by_id
from harmoniq.db.engine import get_db
from harmoniq.modules.hydro.calcule import reservoir_infill

from .core.network_builder import NetworkBuilder
from .utils.energy_utils import EnergyUtils

import pandas as pd
import numpy as np
import pypsa
from typing import List, Dict, Optional, Tuple
import logging

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
    
    def __init__(self, donnees: ListeInfrastructures):
        """
        Initialise l'infrastructure réseau.
        
        Args:
            donnees: Liste des infrastructures incluses dans le réseau
        """
        super().__init__([donnees])
        self.network = None
        self.reservoir_levels = {}
        self.statistics = {}
        self.builder = NetworkBuilder()
        
    def charger_scenario(self, scenario: ScenarioBase):
        """
        Charge le scénario de simulation.
        
        Args:
            scenario: Scénario à utiliser pour la simulation
        """
        self.scenario = scenario
        logger.info(f"Scénario chargé: {scenario.nom}")
        
    @necessite_scenario
    def creer_reseau(self) -> pypsa.Network:
        """
        Crée le réseau électrique à partir des données.
        
        Returns:
            Le réseau PyPSA créé
        """
        logger.info("Création du réseau électrique...")
        
        annee = str(self.scenario.date_de_debut.year)
        
        self.network = self.builder.create_network(self.scenario, annee)
        
        logger.info(f"Réseau créé avec {len(self.network.buses)} bus, "
                   f"{len(self.network.lines)} lignes et "
                   f"{len(self.network.generators)} générateurs")
        
        return self.network

    @necessite_scenario
    def calculer_capacite_import_export(self) -> float:
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
        
        # S'assurer que le réseau existe
        if self.network is None:
            self.creer_reseau()
        
        # Obtention de l'année
        annee = str(self.scenario.date_de_debut.year)
        
        # Récupération des données historiques de production
        energie_historique_HQ = EnergyUtils.obtenir_energie_historique(annee)
        
        # Calcul des besoins énergétiques totaux
        besoins_totaux = self.network.loads_t.p_set.sum().sum()
        
        # Calcul du déséquilibre énergétique global (ΔE)
        deltaE = energie_historique_HQ - besoins_totaux
        
        # Ajustement pour les nouvelles centrales ajoutées par l'utilisateur
        nouvelles_centrales = EnergyUtils.identifier_nouvelles_centrales(self.network)
        for centrale in nouvelles_centrales:
            energie_estimee = EnergyUtils.estimer_production_annuelle(centrale)
            deltaE += energie_estimee
        
        # Calcul de l'import maximal théorique à chaque pas de temps
        import_max_theorique = []
        for heure in self.network.snapshots:
            # Besoins énergétiques à cette heure
            besoins_heure = self.network.loads_t.p_set.loc[heure].sum()
            
            # Production maximale des sources fatales à cette heure
            sources_fatales = self.network.generators[
                self.network.generators.carrier.isin(['hydro_fil', 'eolien', 'solaire'])
            ].index
            
            production_fatale = 0
            if not self.network.generators_t.p_max_pu.empty and len(sources_fatales) > 0:
                production_fatale = sum(
                    self.network.generators.loc[gen, 'p_nom'] * 
                    self.network.generators_t.p_max_pu.loc[heure, gen]
                    for gen in sources_fatales if gen in self.network.generators_t.p_max_pu.columns
                )
            
            # Import maximal théorique = besoins - production fatale
            import_max = besoins_heure - production_fatale
            import_max_theorique.append(import_max)
        
        # Recherche de Pmax pour équilibrer deltaE
        # Initialisation
        Pmax_min = min(import_max_theorique)  # Pourrait être négatif (export)
        Pmax_max = max(import_max_theorique)
        Pmax = (Pmax_min + Pmax_max) / 2
        
        tolerance = 0.1  # Précision souhaitée
        iterations_max = 100
        iteration = 0
        
        # Recherche dichotomique
        while iteration < iterations_max:
            # Calcul des imports/exports avec ce Pmax
            imports = [min(Pmax, max_theorique) for max_theorique in import_max_theorique]
            
            # Somme totale des imports/exports
            somme_imports = sum(imports)
            
            # Vérification de la convergence
            if abs(somme_imports - deltaE) < tolerance:
                break  # Pmax trouvé avec la précision souhaitée
            
            # Ajustement de Pmax
            if somme_imports > deltaE:
                Pmax_max = Pmax  # Trop d'import, réduire Pmax
            else:
                Pmax_min = Pmax  # Pas assez d'import, augmenter Pmax
            
            Pmax = (Pmax_min + Pmax_max) / 2
            iteration += 1
        
        logger.info(f"Pmax calculé: {Pmax:.2f} MW après {iteration} itérations")
        
        # Stockage des informations pour la phase 2
        self.Pmax = Pmax
        self.deltaE = deltaE
        
        return Pmax

    @necessite_scenario
    def optimiser_avec_gestion_reservoirs(self, Pmax: Optional[float] = None) -> Tuple[pypsa.Network, Dict]:
        """
        Phase 2: Optimisation avec gestion adaptative des réservoirs
        
        Cette méthode:
        1. Ajoute un générateur d'import ou une charge d'export selon Pmax
        2. Initialise les niveaux de réservoir
        3. Effectue l'optimisation temporelle avec ajustement des coûts
        4. Collecte les statistiques
        
        Args:
            Pmax: Capacité d'import/export (calcule la capacité si None)
            
        Returns:
            Tuple contenant le réseau optimisé et les statistiques
        """
        logger.info("Phase 2: Optimisation avec gestion adaptative des réservoirs...")
        
        # S'assurer que le réseau existe
        if self.network is None:
            self.creer_reseau()
        
        # Si Pmax n'est pas fourni, le calculer
        if Pmax is None:
            if not hasattr(self, 'Pmax'):
                Pmax = self.calculer_capacite_import_export()
            else:
                Pmax = self.Pmax
        
        # Détermination du type d'échange (import ou export)
        bus_frontiere = EnergyUtils.obtenir_bus_frontiere(self.network, "Interconnexion")
        
        if Pmax > 0:
            # Création d'un générateur d'import
            logger.info(f"Ajout d'un générateur d'import virtuel de {Pmax:.2f} MW")
            self.network.add("Generator", 
                           name="Import_Virtuel",
                           bus=bus_frontiere,
                           p_nom=Pmax,
                           carrier="import",
                           marginal_cost=0.1  # Coût entre les sources fatales et les réservoirs
            )
        else:
            # Création d'une charge d'export (Pmax est négatif)
            logger.info(f"Ajout d'une charge d'export virtuelle de {-Pmax:.2f} MW")
            self.network.add("Load", 
                           name="Export_Virtuel",
                           bus=bus_frontiere,
                           p_set=-Pmax,  # Valeur positive pour une charge
                           type="export"
            )
        
        # Initialisation des niveaux de réservoir
        niveaux_reservoirs = {}
        niveau_initial = {}
        niveau_min = {}
        niveau_max = {}
        
        # Récupération des centrales avec réservoirs
        reservoirs = self.network.generators[self.network.generators.carrier == 'hydro_reservoir'].index
        
        # Initialisation des niveaux
        for gen in reservoirs:
            niveau_initial[gen] = 0.70  # Niveau initial à 70%
            niveaux_reservoirs[gen] = niveau_initial[gen]
        
        # Création de DataFrames pour stocker les niveaux et les coûts
        niveaux_df = pd.DataFrame(index=self.network.snapshots, columns=reservoirs)
        couts_df = pd.DataFrame(index=self.network.snapshots, columns=reservoirs)
        
        # Optimisation temporelle avec gestion des réservoirs
        logger.info("Démarrage de l'optimisation temporelle avec gestion des réservoirs...")
        
        for t, heure_actuelle in enumerate(self.network.snapshots):
            # Mise à jour des coûts marginaux basés sur les niveaux de réservoir
            for generateur in reservoirs:
                niveau = niveaux_reservoirs[generateur]
                cout = EnergyUtils.calcul_cout_reservoir(niveau)
                
                # Enregistrement du niveau et du coût
                niveaux_df.loc[heure_actuelle, generateur] = niveau
                couts_df.loc[heure_actuelle, generateur] = cout
                
                # Mise à jour du coût dans le réseau
                if hasattr(self.network.generators_t, 'marginal_cost'):
                    if generateur in self.network.generators_t.marginal_cost.columns:
                        self.network.generators_t.marginal_cost.loc[heure_actuelle, generateur] = cout
            
            # Optimisation pour cette heure via NetworkBuilder
            snapshot = pd.DatetimeIndex([heure_actuelle])
            self.network.snapshots = snapshot
            self.network = self.builder.optimize_network(self.network)
            
            # Récupération des valeurs de production pour cette heure
            if hasattr(self.network.generators_t, 'p') and not self.network.generators_t.p.empty:
                # Récupération des productions des centrales hydro
                productions_hydro = {}
                for generateur in reservoirs:
                    if generateur in self.network.generators_t.p.columns:
                        productions_hydro[generateur] = self.network.generators_t.p.loc[heure_actuelle, generateur]
                
                productions_df = pd.DataFrame([productions_hydro])
                
                # (0,002 par heure) fct a changer
                apport_naturel = 0.002
                
                niveaux_reservoir_df = reservoir_infill(
                    besoin_puissance=productions_df,
                    pourcentage_reservoir=niveaux_reservoirs,
                    apport_naturel=apport_naturel
                )
                
                # Extraction des valeurs mises à jour et conversion en dictionnaire
                niveaux_reservoirs = niveaux_reservoir_df.iloc[0].to_dict()
        
        # Analyse des flux de puissance via NetworkBuilder
        self.network, _ = self.builder.run_power_flow(self.network, mode="dc")
        
        # Compilation des statistiques finales
        energie_importee = 0
        if "Import_Virtuel" in self.network.generators.index:
            if hasattr(self.network.generators_t, 'p') and "Import_Virtuel" in self.network.generators_t.p.columns:
                energie_importee = self.network.generators_t.p["Import_Virtuel"].sum()
        
        energie_exportee = 0
        if "Export_Virtuel" in self.network.loads.index:
            if hasattr(self.network.loads_t, 'p') and "Export_Virtuel" in self.network.loads_t.p.columns:
                energie_exportee = self.network.loads_t.p["Export_Virtuel"].sum()
        
        self.statistics = {
            "Pmax_calcule": Pmax,
            "deltaE_initial": self.deltaE if hasattr(self, 'deltaE') else None,
            "energie_importee": energie_importee,
            "energie_exportee": energie_exportee,
            "niveaux_finaux_reservoirs": niveaux_reservoirs,
            "niveaux_reservoirs_timeseries": niveaux_df,
            "couts_reservoirs_timeseries": couts_df
        }
        
        logger.info("Optimisation avec gestion des réservoirs terminée avec succès")
        
        self.reservoir_levels = niveaux_reservoirs
        return self.network, self.statistics
    
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
        logger.info("Démarrage du workflow complet d'optimisation avec gestion des imports/exports...")
        
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
        # Exécuter le workflow complet si pas encore fait
        if self.network is None or not self.statistics:
            self.workflow_import_export()
        
        # Agréger les données de production par type d'énergie
        if hasattr(self.network, 'generators_t') and hasattr(self.network.generators_t, 'p'):
            production = self.network.generators_t.p.copy()
            
            # Ajouter une colonne pour la production totale
            production['totale'] = production.sum(axis=1)
            
            # Ajouter des colonnes par type d'énergie
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

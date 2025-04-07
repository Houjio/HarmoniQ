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
    def creer_reseau(self) -> pypsa.Network:
        """
        Crée le réseau électrique à partir des données, avec mise en cache.
        
        Cette méthode vérifie d'abord si un réseau précalculé existe en cache.
        Si c'est le cas, elle le charge, sinon elle en crée un nouveau et le sauvegarde.
        
        Returns:
            Le réseau PyPSA créé ou chargé depuis le cache
        """
        import os
        import hashlib
        
        # Générer un nom de fichier unique pour ce scénario
        scenario_id = getattr(self.scenario, 'id', 0)
        scenario_name = getattr(self.scenario, 'nom', 'default').replace(' ', '_')
        scenario_date = getattr(self.scenario, 'date_de_debut', None)
        scenario_year = scenario_date.year if scenario_date else "unknown"
        
        # Générer un identifiant pour la liste d'infrastructures
        infra_id = getattr(self.donnees, 'id', 0)
        
        # Générer un hash d'empreinte pour les infrastructures
        infra_hash = ""
        try:
            infra_str = str(self.donnees.__dict__)
            infra_hash = hashlib.md5(infra_str.encode()).hexdigest()[:8]
        except Exception as e:
            logger.warning(f"Erreur lors de la génération du hash d'infrastructure: {e}")
            infra_hash = str(infra_id)
        
        # Créer un dossier pour les réseaux sauvegardés s'il n'existe pas
        cache_dir = DATA_DIR.parent / "network_cache"
        os.makedirs(cache_dir, exist_ok=True)
        
        # Nom du fichier de cache avec scénario ET liste d'infrastructures
        network_filename = f"network_s{scenario_id}_{scenario_year}_i{infra_id}_{infra_hash}.nc"
        network_path = cache_dir / network_filename
        
        # Vérifier si un réseau précalculé existe
        if network_path.exists():
            logger.info(f"Chargement du réseau précalculé depuis {network_path}")
            try:
                network = pypsa.Network()
                network.import_from_netcdf(str(network_path))
                self.network = network
                logger.info(f"Réseau chargé avec succès: {len(network.buses)} bus, " 
                            f"{len(network.lines)} lignes, {len(network.generators)} générateurs")
                return self.network
            except Exception as e:
                logger.warning(f"Erreur lors du chargement du réseau précalculé: {e}")
                logger.info("Création d'un nouveau réseau...")
        else:
            logger.info(f"Aucun réseau précalculé trouvé, création d'un nouveau réseau...")
        
        # Création normale du réseau
        logger.info("Création du réseau électrique...")
        
        annee = str(self.scenario.date_de_debut.year)
        start_date = self.scenario.date_de_debut
        end_date = self.scenario.date_de_fin
        
        network = self.builder.create_network(self.scenario, annee, start_date, end_date)
        
        # Sauvegarder le réseau pour une utilisation future
        try:
            logger.info(f"Sauvegarde du réseau vers {network_path}")
            network.export_to_netcdf(str(network_path))
            logger.info("Réseau sauvegardé avec succès")
        except Exception as e:
            logger.warning(f"Erreur lors de la sauvegarde du réseau: {e}")
        
        self.network = network
        
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
        
        if self.network is None:
            self.creer_reseau()
        
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
            # Besoins énergétiques
            besoins_heure = self.network.loads_t.p_set.loc[heure].sum()
            
            # Production maximale des sources fatales
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
        
        if self.network is None:
            self.creer_reseau()
        
        if Pmax is None:
            if not hasattr(self, 'Pmax'):
                Pmax = self.calculer_capacite_import_export()
            else:
                Pmax = self.Pmax
        
        # Détermination du type d'échange (import ou export)
        bus_frontiere = EnergyUtils.obtenir_bus_frontiere(self.network, "Interconnexion") #bus_type pas utilisé pour le moment
        
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
                           name="load_export",
                           bus=bus_frontiere,
                           p_set=-Pmax,  # Valeur positive pour une charge
                           type="export"
            )
        
        reservoirs = self.network.generators[self.network.generators.carrier == 'hydro_reservoir'].index
        
        niveaux_initiaux = {gen: 0.70 for gen in reservoirs}  # Niveau initial à 70%
        niveaux_reservoirs_df = pd.DataFrame([niveaux_initiaux])
        
        niveaux_df = pd.DataFrame(index=self.network.snapshots, columns=reservoirs)
        couts_df = pd.DataFrame(index=self.network.snapshots, columns=reservoirs)
        
        # Optimisation avec gestion des réservoirs
        logger.info("Démarrage de l'optimisation temporelle avec gestion des réservoirs...")
        
        for t, heure_actuelle in enumerate(self.network.snapshots):
            niveaux_actuels = niveaux_reservoirs_df.iloc[0]
            for generateur in reservoirs:
                niveau = niveaux_actuels[generateur]
                cout = EnergyUtils.calcul_cout_reservoir(niveau)
                
                niveaux_df.loc[heure_actuelle, generateur] = niveau
                couts_df.loc[heure_actuelle, generateur] = cout
                
                # Mise à jour du coût
                if hasattr(self.network.generators_t, 'marginal_cost'):
                    if generateur in self.network.generators_t.marginal_cost.columns:
                        self.network.generators_t.marginal_cost.loc[heure_actuelle, generateur] = cout
            
            snapshot = pd.DatetimeIndex([heure_actuelle])
            self.network.snapshots = snapshot
            self.network = self.builder.optimize_network(self.network)
            
            # Récupération des valeurs de production
            if hasattr(self.network.generators_t, 'p') and not self.network.generators_t.p.empty:
                productions_hydro = {}
                for generateur in reservoirs:
                    if generateur in self.network.generators_t.p.columns:
                        productions_hydro[generateur] = self.network.generators_t.p.loc[heure_actuelle, generateur]
                
                productions_df = pd.DataFrame([productions_hydro])
                
                # Mise à jour des niveaux
                niveaux_reservoirs_df = EnergyUtils.get_niveau_reservoir(
                    productions=productions_df,
                    niveaux_actuels=niveaux_reservoirs_df,
                    timestamp=heure_actuelle
                )
        
        self.network, _ = self.builder.run_power_flow(self.network, mode="dc")
        
        energie_importee = 0
        if "Import_Virtuel" in self.network.generators.index:
            if hasattr(self.network.generators_t, 'p') and "Import_Virtuel" in self.network.generators_t.p.columns:
                energie_importee = self.network.generators_t.p["Import_Virtuel"].sum()
        
        energie_exportee = 0
        if "Export_Virtuel" in self.network.loads.index:
            if hasattr(self.network.loads_t, 'p') and "Export_Virtuel" in self.network.loads_t.p.columns:
                energie_exportee = self.network.loads_t.p["Export_Virtuel"].sum()
        
        niveaux_finaux = niveaux_reservoirs_df.iloc[0].to_dict()
        
        self.statistics = {
            "Pmax_calcule": Pmax,
            "deltaE_initial": self.deltaE if hasattr(self, 'deltaE') else None,
            "energie_importee": energie_importee,
            "energie_exportee": energie_exportee,
            "niveaux_finaux_reservoirs": niveaux_finaux,
            "niveaux_reservoirs_timeseries": niveaux_df,
            "couts_reservoirs_timeseries": couts_df
        }
        
        logger.info("Optimisation avec gestion des réservoirs terminée avec succès")
        
        self.reservoir_levels = niveaux_finaux
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

#TODO : A SUPPRIMER
    @necessite_scenario
    def calculer_capacite_import_export_2020(self) -> float:
        """
        Version adaptée du calcul de capacité d'import/export utilisant l'année 2020 pour les timestamps.
        
        Cette méthode est identique à calculer_capacite_import_export mais convertit 
        les timestamps vers 2020 pour éviter les erreurs de clé.
        
        Returns:
            Capacité maximale d'import/export calculée (Pmax)
        """
        logger.info("Phase 1: Calcul de la capacité d'import/export (version 2020)...")
        
        if self.network is None:
            self.creer_reseau()
        
        # Adapter les snapshots pour l'année 2020
        snapshots_originaux = self.network.snapshots
        snapshots_2020 = pd.DatetimeIndex([
            pd.Timestamp(
                year=2020,
                month=ts.month,
                day=ts.day,
                hour=ts.hour,
                minute=ts.minute
            ) for ts in snapshots_originaux
        ])
        
        # Créer un mapping entre dates originales et dates 2020
        mapping_dates = dict(zip(snapshots_originaux, snapshots_2020))
        
        # Adapter les loads_t.p_set
        p_set_original = self.network.loads_t.p_set.copy()
        p_set_2020 = p_set_original.copy()
        p_set_2020.index = snapshots_2020
        
        # Calculer comme dans la méthode originale
        annee = str(self.scenario.date_de_debut.year)
        
        energie_historique_HQ = EnergyUtils.obtenir_energie_historique(annee)
        besoins_totaux = p_set_2020.sum().sum()
        # Calcul du déséquilibre énergétique global (ΔE)
        deltaE = energie_historique_HQ - besoins_totaux
        
        # Ajustement pour les nouvelles centrales ajoutées
        nouvelles_centrales = EnergyUtils.identifier_nouvelles_centrales(self.network)
        for centrale in nouvelles_centrales:
            energie_estimee = EnergyUtils.estimer_production_annuelle(centrale)
            deltaE += energie_estimee
        
        # Calcul de l'import maximal théorique à chaque pas de temps
        import_max_theorique = []
        
        for heure_orig in snapshots_originaux:
            heure_2020 = mapping_dates[heure_orig]
            
            # Besoins énergétiques (utiliser p_set_2020)
            besoins_heure = p_set_2020.loc[heure_2020].sum()
            
            # Production maximale des sources fatales
            sources_fatales = self.network.generators[
                self.network.generators.carrier.isin(['hydro_fil', 'eolien', 'solaire'])
            ].index
            
            production_fatale = 0
            if not self.network.generators_t.p_max_pu.empty and len(sources_fatales) > 0:
                production_fatale = sum(
                    self.network.generators.loc[gen, 'p_nom'] * 
                    self.network.generators_t.p_max_pu.loc[heure_orig, gen]
                    for gen in sources_fatales if gen in self.network.generators_t.p_max_pu.columns
                )
            
            # Import maximal théorique = besoins - production fatale
            import_max = besoins_heure - production_fatale
            import_max_theorique.append(import_max)
        
        # Recherche de Pmax pour équilibrer deltaE
        Pmax_min = min(import_max_theorique)  # Pourrait être négatif (export)
        Pmax_max = max(import_max_theorique)
        Pmax = (Pmax_min + Pmax_max) / 2
        
        tolerance = 10
        iterations_max = 1000
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
        
        logger.info(f"Pmax calculé (version 2020): {Pmax:.2f} MW après {iteration} itérations")
        
        self.Pmax = Pmax
        self.deltaE = deltaE
        
        return Pmax

if __name__ == "__main__":
    from harmoniq.db.CRUD import read_data_by_id, read_all_scenario
    from harmoniq.db.engine import get_db
    from harmoniq.db.schemas import ListeInfrastructures
    import asyncio
    
    db = next(get_db())
    
    liste_infrastructures = asyncio.run(read_data_by_id(db, ListeInfrastructures, 2))
    infraReseau = InfraReseau(liste_infrastructures)
    
    scenario = read_all_scenario(db)[2]
    infraReseau.charger_scenario(scenario)

    Pmax = infraReseau.calculer_capacite_import_export_2020()
    
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


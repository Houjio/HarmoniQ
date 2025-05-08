from harmoniq.core.base import Infrastructure, necessite_scenario
from harmoniq.db.schemas import ScenarioBase, Hydro, ListeInfrastructures
from harmoniq.db.CRUD import read_all_hydro, read_multiple_by_id
from harmoniq.db.engine import get_db

from harmoniq.modules.reseau.core import NetworkBuilder, PowerFlowAnalyzer, NetworkOptimizer
from harmoniq.modules.reseau.utils import EnergyUtils

import pandas as pd
import numpy as np
import pypsa
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path
import os
import hashlib

logger = logging.getLogger("Reseau")

MODULES_DIR = Path(__file__).parent
NETWORK_CACHE_DIR = MODULES_DIR / "n_cache"/ "network_cache"
os.makedirs(NETWORK_CACHE_DIR, exist_ok=True)


class InfraReseau(Infrastructure):
    """
    Gestion du réseau électrique avec optimisation des imports/exports
    et pilotage adaptatif des réservoirs.
    
    Cette classe implémente le workflow complet du réseau électrique:
    1. Chargement et création du réseau
    2. Calcul de la capacité d'import/export
    3. Optimisation temporelle avec gestion des réservoirs
    4. Analyse des résultats
    """
    
    def __init__(self, donnees: ListeInfrastructures, data_dir: str = None):
        """
        Args:
            donnees: Liste des infrastructures incluses dans le réseau
            data_dir: Chemin vers le répertoire des données (optionnel)
        """
        super().__init__([donnees])
        self.network = None
        self.reservoir_levels = {}
        self.statistics = {}
        self.builder = NetworkBuilder(data_dir)
        self.is_journalier = False  # Par défaut, le mode horaire est utilisé
        
    def charger_scenario(self, scenario: ScenarioBase):

        self.scenario = scenario
        logger.info(f"Scénario chargé: {scenario.nom}")
        
    @necessite_scenario
    async def creer_reseau(self, liste_infra=None) -> pypsa.Network: #Ne sert uniquement à créer le reseau que si il n'est pas déja crée, ce qui n'arrive à priori pas
        """
        Crée un réseau PyPSA complet à partir des données statiques
        et des séries temporelles associées au scénario, avec mise en cache.
        
        Args:
            liste_infra: Liste des infrastructures à inclure dans le réseau (optionnel)
        
        Returns:
            pypsa.Network: Réseau prêt pour l'optimisation
        """
        if liste_infra is None:
            liste_infra = self.donnees
            
        # Générer un identifiant unique pour la configuration
        scenario_id = getattr(self.scenario, 'id', 0)
        scenario_date = getattr(self.scenario, 'date_de_debut', None)
        scenario_year = scenario_date.year if scenario_date else "unknown"
        
        # Créer une signature unique pour la liste d'infrastructures
        infra_id = getattr(liste_infra, 'id', 0)
        infra_hash = str(infra_id)
        try:
            infra_str = str(liste_infra.dict()) if hasattr(liste_infra, 'dict') else str(infra_id)
            infra_hash = hashlib.md5(infra_str.encode()).hexdigest()[:8]
        except Exception:
            pass
        
        network_filename = f"network_s{scenario_id}_{scenario_year}_i{infra_id}_{infra_hash}.nc"
        network_path = NETWORK_CACHE_DIR / network_filename
        
        # Vérifier si un réseau précalculé existe
        if network_path.exists():
            logger.info(f"Chargement du réseau précalculé depuis {network_path}")
            try:
                network = pypsa.Network()
                network.import_from_netcdf(str(network_path))
                
                self.network = network
                logger.info(f"Réseau chargé: {len(network.buses)} bus, {len(network.lines)} lignes, {len(network.generators)} générateurs")
                return network
                
            except Exception as e:
                logger.warning(f"Erreur lors du chargement du réseau: {e}")
                try:
                    os.remove(network_path)
                    logger.info(f"Fichier cache supprimé: {network_path}")
                except:
                    pass
        
        # Création d'un nouveau réseau
        logger.info("Création d'un nouveau réseau électrique")
        
        annee = str(self.scenario.date_de_debut.year)
        start_date = self.scenario.date_de_debut
        end_date = self.scenario.date_de_fin
        
        network = await self.builder.create_network(self.scenario, liste_infra, annee, start_date, end_date)
        
        
        # Normaliser les types de données avant sauvegarde
        self._normaliser_types_reseau(network)
        
        # Sauvegarder en format netCDF
        try:
            network.export_to_netcdf(str(network_path))
            logger.info("Réseau sauvegardé avec succès")
        except Exception as e:
            logger.warning(f"Erreur lors de la sauvegarde du réseau: {e}")
        
        self.network = network
        logger.info(f"Réseau créé: {len(network.buses)} bus, {len(network.lines)} lignes, {len(network.generators)} générateurs")
        
        return network

    def _normaliser_types_reseau(self, network): #normalise les types de données pour la sauvegarde
        """
        Normalise les types de données dans le réseau pour la sauvegarde.
        
        Args:
            network: Réseau PyPSA à normaliser
        """
        if 'type' in network.buses.columns:
            network.buses.type = network.buses.type.astype(str)
        
        for component in ['generators', 'loads', 'lines', 'transformers']:
            df = getattr(network, component)
            for col in df.columns:
                if df[col].dtype == 'object':
                    try:
                        df[col] = df[col].astype(str)
                    except:
                        pass

    @necessite_scenario
    async def calculer_capacite_import_export(self, liste_infra) -> float:
        """
        Calcule la capacité maximale d'import/export (Pmax) en équilibrant
        le déséquilibre énergétique global.
        
        Args:
            liste_infra: Liste des infrastructures du réseau
            
        Returns:
            float: Capacité maximale d'import/export calculée (Pmax)
        """
        logger.info("Calcul de la capacité d'import/export...")
        
        if self.network is None:
            await self.creer_reseau(liste_infra)
        
        annee = str(self.scenario.date_de_debut.year)
        
        energie_historique_HQ = EnergyUtils.obtenir_energie_historique(annee)
        besoins_totaux = self.network.loads_t.p_set.sum().sum()
        deltaE = energie_historique_HQ - besoins_totaux
        
        # Ajustement pour les nouvelles centrales
        nouvelles_centrales = EnergyUtils.identifier_nouvelles_centrales(self.network)
        for centrale in nouvelles_centrales:
            energie_estimee = EnergyUtils.estimer_production_annuelle(centrale)
            deltaE += energie_estimee
        
        # Calcul de l'import maximal théorique à chaque pas de temps
        import_max_theorique = []
        for heure in self.network.snapshots:
            try:
                # Besoins énergétiques
                besoins_df = self.network.loads_t.p_set.loc[heure]
                print("Besoins à l'heure ", heure, " : ", besoins_df)
                besoins_heure = besoins_df.sum() if isinstance(besoins_df, pd.Series) else besoins_df.sum().sum()
                besoins_heure = float(besoins_heure)
                print("Les besoins à l'heure ", heure, " sont ", besoins_heure)
                
                # Production des sources fatales
                sources_fatales = self.network.generators[
                    self.network.generators.carrier.isin(['hydro_fil', 'eolien', 'solaire'])
                ].index
                
                production_fatale = 0
                if not self.network.generators_t.p_max_pu.empty and len(sources_fatales) > 0:
                    for gen in sources_fatales:
                        if gen in self.network.generators_t.p_max_pu.columns:
                            p_nom = float(self.network.generators.loc[gen, 'p_nom'])
                            p_max_pu_val = float(self.network.generators_t.p_max_pu.loc[heure, gen])
                            
                            if pd.isna(p_nom) or pd.isna(p_max_pu_val):
                                continue
                                
                            production_fatale += p_nom * p_max_pu_val
                
                import_max = besoins_heure - production_fatale
                import_max_theorique.append(import_max)
            
            except Exception as e:
                logger.error(f"Erreur lors du calcul pour {heure}: {str(e)}")
                import_max_theorique.append(0.0)
        
        # Recherche de Pmax par dichotomie
        Pmax_min = min(import_max_theorique)
        Pmax_max = max(import_max_theorique)
        Pmax = (Pmax_min + Pmax_max) / 2
        
        tolerance = 0.1
        iterations_max = 100
        
        for iteration in range(iterations_max):
            imports = [min(Pmax, max_theorique) for max_theorique in import_max_theorique]
            somme_imports = sum(imports)
            
            if abs(somme_imports - deltaE) < tolerance:
                break
            
            if somme_imports > deltaE:
                Pmax_max = Pmax
            else:
                Pmax_min = Pmax
            
            Pmax = (Pmax_min + Pmax_max) / 2
        
        logger.info(f"Pmax calculé: {Pmax:.2f} MW après {iteration+1} itérations")
        
        self.Pmax = Pmax
        self.deltaE = deltaE
        
        return Pmax

    @necessite_scenario
    async def fake_optimiser_reservoirs(self, liste_infra, Pmax=None, is_journalier=None) -> Tuple[pypsa.Network, Dict]:
        """
        Optimise le réseau avec une gestion simulée des réservoirs.
        
        Cette méthode:
        1. Génère des faux niveaux de réservoir 
        2. Calcule les coûts marginaux basés sur ces niveaux
        3. Optimise le réseau avec NetworkOptimizer
        
        Args:
            liste_infra: Liste des infrastructures du réseau
            Pmax: Capacité maximale d'import/export (MW)
            is_journalier: Si True, utilise un pas de temps journalier (24h)
            
        Returns:
            Tuple[network, statistics]: Réseau optimisé et statistiques
        """
        logger.info("Optimisation avec gestion simulée des réservoirs...")
        
        # Utiliser la valeur transmise ou la valeur par défaut de l'instance
        is_journalier = self.is_journalier if is_journalier is None else is_journalier
        
        if self.network is None:
            await self.creer_reseau(liste_infra)
        
        if Pmax is None:
            if not hasattr(self, 'Pmax'):
                Pmax = await self.calculer_capacite_import_export(liste_infra)
            else:
                Pmax = self.Pmax
        
        # Réechantillonner à une fréquence journalière si demandé
        if is_journalier:
            logger.info("Passage en mode journalier (pas de temps = 24h)")
            self.network = EnergyUtils.reechantillonner_reseau_journalier(self.network)
        
        barrages_reservoir = self.network.generators[
            self.network.generators.carrier == 'hydro_reservoir'
        ].index.tolist()
        
        if not barrages_reservoir:
            logger.warning("Aucun barrage à réservoir trouvé dans le réseau")
            return self.network, {}
        
        # Générer des niveaux de réservoir simulés
        niveaux_reservoirs = EnergyUtils.generer_faux_niveaux_reservoirs(
            self.network.snapshots, barrages_reservoir
        )
        
        # Calculer les coûts marginaux basés sur les niveaux
        marginal_costs = pd.DataFrame(index=self.network.snapshots)
        for barrage in barrages_reservoir:
            costs = []
            for timestamp in self.network.snapshots:
                niveau = niveaux_reservoirs.loc[timestamp, barrage]
                costs.append(EnergyUtils.calcul_cout_reservoir(niveau))
            marginal_costs[barrage] = costs
        
        # Ajouter les coûts marginaux au réseau
        if not hasattr(self.network, 'generators_t'):
            self.network.generators_t = {}
        if 'marginal_cost' not in self.network.generators_t:
            self.network.generators_t['marginal_cost'] = pd.DataFrame(index=self.network.snapshots)
        
        for barrage in barrages_reservoir:
            self.network.generators_t['marginal_cost'][barrage] = marginal_costs[barrage]

        # Ajouter l'interconnexion et vérifier la connectivité
        bus_frontiere = EnergyUtils.obtenir_bus_frontiere(self.network, "Interconnexion")
        self.network = EnergyUtils.ajouter_interconnexion_import_export(self.network, Pmax)
        self.network = EnergyUtils.ensure_network_solvability(self.network)
        
        # Optimiser le réseau avec l'optimisateur manuel au lieu de PyPSA standard
        optimizer = NetworkOptimizer(self.network, is_journalier=is_journalier)
        # On vérifie quand même la faisabilité pour information
        feasible, message = optimizer.check_optimization_feasibility()
        logger.info(f"Feasibility check: {feasible}, {message}")
        
        # Utilise notre méthode d'optimisation manuelle
        optimized_network = optimizer.optimize_manually()
        optimization_results = optimizer.get_optimization_results()

        statistics = {
            "Pmax_calcule": Pmax,
            "niveaux_reservoirs": niveaux_reservoirs,
            "optimization_results": optimization_results,
            "production_par_type": optimized_network.generators_t['p'].groupby(
                optimized_network.generators.carrier, axis=1
            ).sum(),
            "energie_importee": optimized_network.generators_t['p'].get(f"import_{bus_frontiere}", pd.Series()).sum() 
                if f"import_{bus_frontiere}" in optimized_network.generators_t['p'].columns else 0,
            "energie_exportee": optimized_network.loads_t['p'].get(f"export_{bus_frontiere}", pd.Series()).sum() 
                if f"export_{bus_frontiere}" in optimized_network.loads_t['p'].columns else 0
        }
        
        self.statistics = statistics
        self.network = optimized_network
        return optimized_network, statistics

    @necessite_scenario
    async def optimiser_avec_gestion_reservoirs(self, liste_infra, Pmax=None, is_journalier=None) -> pypsa.Network:
        """
        Optimisation avec gestion dynamique des réservoirs.
        
        Cette méthode n'est pas encore complètement implémentée.
        Son but est de faire l'optimisation avec une gestion dynamique des niveaux 
        de réservoir à chaque pas de temps, en tenant compte des apports naturels 
        et des contraintes hydrauliques.
        
        Args:
            liste_infra: Liste des infrastructures du réseau
            Pmax: Capacité maximale d'import/export (MW)
            is_journalier: Si True, utilise un pas de temps journalier (24h)
        
        Returns:
            pypsa.Network: Réseau optimisé
        """
        logger.info("Optimisation avec gestion des réservoirs...")
        
        # Utiliser la valeur transmise ou la valeur par défaut de l'instance
        is_journalier = self.is_journalier if is_journalier is None else is_journalier
        
        if self.network is None:
            await self.creer_reseau(liste_infra)
        
        if Pmax is None:
            if not hasattr(self, 'Pmax'):
                Pmax = await self.calculer_capacite_import_export(liste_infra)
            else:
                Pmax = self.Pmax
        
        network, _ = await self.fake_optimiser_reservoirs(liste_infra, Pmax, is_journalier)
        return network

    @necessite_scenario
    async def workflow_import_export(self, liste_infra, is_journalier=False) -> Tuple[pypsa.Network, Dict]:
        """
        Exécute le workflow complet d'import/export avec gestion des réservoirs.
        
        Cette méthode combine les deux phases:
        1. Calcul de la capacité d'import/export
        2. Optimisation avec gestion des réservoirs
        
        Args:
            liste_infra: Liste des infrastructures du réseau
            is_journalier: Si True, utilise un pas de temps journalier (24h)
        
        Returns:
            Tuple[network, statistics]: Réseau optimisé et statistiques
        """
        logger.info(f"Démarrage du workflow d'optimisation en mode {'journalier' if is_journalier else 'horaire'}...")
        
        # Mettre à jour le mode de l'instance
        self.is_journalier = is_journalier
        
        Pmax = await self.calculer_capacite_import_export(liste_infra)
        network, statistics = await self.fake_optimiser_reservoirs(liste_infra, Pmax, is_journalier)
        
        logger.info("Workflow d'optimisation terminé")
        return network, statistics
    
    async def calculer_production(self, liste_infra, is_journalier=False) -> pd.DataFrame:
        """
        Calcule la production optimisée par type d'énergie.
        """
        if self.network is None or not self.statistics:
            await self.workflow_import_export(liste_infra, is_journalier)
        
        if not hasattr(self.network, 'generators_t') or not hasattr(self.network.generators_t, 'p'):
            logger.error("Aucune donnée de production disponible")
            return pd.DataFrame()
            
        # Détecter si nous avons des snapshots journaliers ou horaires
        daily_snapshots = False
        if len(self.network.snapshots) > 1:
            time_diff = self.network.snapshots[1] - self.network.snapshots[0]
            if time_diff >= pd.Timedelta(hours=23):
                daily_snapshots = True
                period = 'daily'
                logger.info(f"Snapshots journaliers détectés (écart: {time_diff})")
            else:
                period = 'hourly'
                logger.info(f"Snapshots horazires détectés (écart: {time_diff})")
                
        production_power = self.network.generators_t['p'].copy()
        
        # Regrouper tous les générateurs d'urgence en une seule colonne
        emergency_gens = [col for col in production_power.columns if col.startswith('emergency_gen_')]
        if emergency_gens:
            production_power['total_emergency'] = production_power[emergency_gens].sum(axis=1)
            production_power = production_power.drop(columns=emergency_gens)
            logger.info(f"Regroupement de {len(emergency_gens)} générateurs d'urgence en une seule colonne")
        
        # Convertir les puissances en énergie (MWh)
        production = EnergyUtils.calculate_energy_from_power(self.network, production_power)
        
        # Calculer l'énergie totale produite sur toute la période
        production['totale'] = production.sum(axis=1)
        
        # Calculer l'énergie totale pour chaque type de production
        carriers = self.network.generators.carrier.unique()
        for carrier in carriers:
            gens = self.network.generators[self.network.generators.carrier == carrier].index
            if len(gens) > 0:
                # Exclure les générateurs d'urgence déjà regroupés
                gens = [g for g in gens if not g.startswith('emergency_gen_')]
                if gens:  # S'assurer qu'il reste des générateurs à sommer
                    production[f'total_{carrier}'] = production[gens].sum(axis=1)
        
        # Ajouter une colonne spécifique pour les générateurs d'urgence
        if 'total_emergency' in production_power.columns:
            carrier = 'emergency'
            if f'total_{carrier}' not in production.columns:
                production[f'total_{carrier}'] = production['total_emergency']
        
        total_production_mwh = production['totale'].sum()
        logger.info(f"Énergie totale calculée: {total_production_mwh:.2f} MWh ({total_production_mwh/1e6:.4f} TWh)")
        
        for carrier in list(carriers) + (['emergency'] if 'total_emergency' in production_power.columns else []):
            carrier_col = f'total_{carrier}'
            if carrier_col in production.columns:
                carrier_total = production[carrier_col].sum()
                percentage = 100 * carrier_total / total_production_mwh if total_production_mwh > 0 else 0
                logger.info(f"Énergie {carrier}: {carrier_total:.2f} MWh ({percentage:.2f}%)")
        
        return production

if __name__ == "__main__":
    from harmoniq.db.CRUD import read_data_by_id, read_all_scenario
    from harmoniq.db.engine import get_db
    from harmoniq.db.schemas import ListeInfrastructures
    import asyncio
    
    db = next(get_db())
    
    liste_infrastructures = asyncio.run(read_data_by_id(db, ListeInfrastructures, 1))
    infraReseau = InfraReseau(liste_infrastructures)
    
    scenario = read_all_scenario(db)[1]
    infraReseau.charger_scenario(scenario)

    network, statistics = asyncio.run(infraReseau.workflow_import_export(liste_infrastructures, is_journalier=True))
    print(f"Mode journalier activé: calculs réalisés avec un pas de 24h")
    print(f"Capacité d'import/export (Pmax): {statistics['Pmax_calcule']:.2f} MW")
    
    import_energy = EnergyUtils.calculate_energy_from_power(network, statistics['energie_importee'])
    export_energy = EnergyUtils.calculate_energy_from_power(network, statistics['energie_exportee'])
    
    print(f"Énergie importée: {import_energy:.2f} MWh")
    print(f"Énergie exportée: {export_energy:.2f} MWh")
    
    production = infraReseau.calculer_production(liste_infrastructures)
    
    print(f"Production totale: {production['totale'].sum():.2f} MWh")
    
    print("\nProduction par type d'énergie:")
    carriers = network.generators.carrier.unique()
    for carrier in carriers:
        print(f"- {carrier}: {production[f'total_{carrier}'].sum():.2f} MWh")
    
    # EnergyUtils.debug_network_energy_allocation(network, 'daily')



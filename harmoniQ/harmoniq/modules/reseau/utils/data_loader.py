"""
Module de chargement des données pour le réseau électrique.

Ce module gère le chargement des données statiques et temporelles 
du réseau électrique d'Hydro-Québec pour la configuration du réseau 
et les séries temporelles de production/consommation.
"""

import pypsa
import pandas as pd
from pathlib import Path
from typing import Optional
from .geo_utils import GeoUtils
import asyncio
import numpy as np
import os
import hashlib
from harmoniq.modules.eolienne import InfraParcEolienne
from harmoniq.modules.solaire import InfraSolaire
from harmoniq.modules.nucleaire import InfraNucleaire
from harmoniq.db.engine import get_db
from harmoniq.db.demande import read_demande_data
from harmoniq.db.schemas import EolienneParc, Solaire, Hydro, Nucleaire, Thermique, Scenario, BusType
from harmoniq.db.CRUD import (read_all_bus_async, read_all_line_async, read_all_line_type_async,
                              read_all_eolienne_parc, read_all_solaire, read_all_hydro,
                              read_all_nucleaire, read_all_thermique, read_multiple_by_id, read_all_data)


CURRENT_DIR = Path(__file__).parent
DATA_DIR = CURRENT_DIR / ".." / "data"

MODULES_DIR = Path(__file__).parent.parent.parent.parent
RESEAU_DIR = MODULES_DIR / "modules" / "reseau"
DEMAND_CACHE_DIR = RESEAU_DIR / "n_cache"/ "demand_cache"
os.makedirs(DEMAND_CACHE_DIR, exist_ok=True)

import logging
logger = logging.getLogger("DataLoader")


class DataLoadError(Exception):
    """Exception levée lors d'erreurs de chargement des données."""
    pass


class NetworkDataLoader:
    """
    Gestionnaire de chargement des données du réseau.
    
    Charge les données du réseau à partir des fichiers CSV et de la base de données.
    
    Attributes:
        data_dir: Chemin vers le répertoire des données
        eolienne_ids, solaire_ids, hydro_ids, etc: IDs des infrastructures à inclure
    """

    def __init__(self, data_dir: str = None):
        """
        Initialise le chargeur de données.
        
        Args:
            data_dir: Chemin vers le répertoire des données (optionnel)
            
        Raises:
            DataLoadError: Si le répertoire n'existe pas
        """
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
            
        if not self.data_dir.exists():
            raise DataLoadError(f"Le répertoire {self.data_dir} n'existe pas")
        
        self.eolienne_ids = None
        self.solaire_ids = None
        self.hydro_ids = None
        self.thermique_ids = None
        self.nucleaire_ids = None

    def set_infrastructure_ids(self, liste_infra):
        """
        Configure les IDs des infrastructures à charger.
        
        Args:
            liste_infra: Objet ListeInfrastructures contenant les IDs
        """
        if liste_infra.parc_eoliens:
            self.eolienne_ids = [int(id) for id in liste_infra.parc_eoliens.split(',')]
        
        if liste_infra.parc_solaires:
            self.solaire_ids = [int(id) for id in liste_infra.parc_solaires.split(',')]
        
        if liste_infra.central_hydroelectriques:
            self.hydro_ids = [int(id) for id in liste_infra.central_hydroelectriques.split(',')]
        
        if liste_infra.central_thermique:
            self.thermique_ids = [int(id) for id in liste_infra.central_thermique.split(',')]

    async def load_network_data(self) -> pypsa.Network:
        """
        Charge les données statiques du réseau.
        
        Charge la topologie du réseau (buses, lignes, générateurs)
        depuis la base de données.
        
        Returns:
            pypsa.Network: Réseau PyPSA configuré avec les données statiques
            
        Raises:
            DataLoadError: Si les données sont inaccessibles ou mal formatées
        """
        network = pypsa.Network()
        db = next(get_db())
        
        # Chargement des bus
        buses =  await read_all_bus_async(db)
        buses_df = pd.DataFrame([bus.__dict__ for bus in buses])
        if not buses_df.empty:
            buses_df = buses_df.drop(columns=['_sa_instance_state'], errors='ignore')
            buses_df = buses_df.set_index('name')
            
            for idx, row in buses_df.iterrows():
                network.add("Bus", name=idx, **row.to_dict())
                # Création des charges pour les bus de type "conso"
                if row.get('type') == 'conso':
                    network.add("Load", 
                              name=f"load_{idx}",
                              bus=idx,
                              p_set=0,  
                              q_set=0
                    )
        
        # Chargement des types de lignes
        line_types = await read_all_line_type_async(db)
        line_types_df = pd.DataFrame([lt.__dict__ for lt in line_types])
        if not line_types_df.empty:
            line_types_df = line_types_df.drop(columns=['_sa_instance_state'], errors='ignore')
            line_types_df = line_types_df.set_index('name')
            
            for idx, row in line_types_df.iterrows():
                network.add("LineType", name=idx, **row.to_dict())
        
        # Chargement des lignes
        lines = await read_all_line_async(db)
        lines_df = pd.DataFrame([line.__dict__ for line in lines])
        if not lines_df.empty:
            lines_df = lines_df.drop(columns=['_sa_instance_state'], errors='ignore')
            lines_df = lines_df.set_index('name')
            
            for idx, row in lines_df.iterrows():
                network.add("Line", name=idx, **row.to_dict())

        # Chargement des carriers
        carriers_df = pd.read_csv(self.data_dir / "topology" / "centrales" / "carriers.csv")
        carriers_df = carriers_df.set_index('name')
        for idx, row in carriers_df.iterrows():
            network.add("Carrier", name=idx, **row.to_dict())

        # Chargement des générateurs par type
        network = await self.fill_non_pilotable(network, "eolienne")
        network = await self.fill_non_pilotable(network, "solaire")
        network = await self.fill_non_pilotable(network, "hydro_fil")
        network = await self.fill_non_pilotable(network, "nucleaire")
        network = await self.fill_pilotable(network, "hydro_reservoir")
        network = await self.fill_pilotable(network, "thermique")
        
        # Chargement des contraintes globales
        global_constraints_df = pd.read_csv(
            self.data_dir / "topology" / "constraints" / "global_constraints.csv"
        ).set_index('name')
        for idx, row in global_constraints_df.iterrows():
            network.add("GlobalConstraint", name=idx, **row.to_dict())
            
        return network

    async def load_timeseries_data(self, 
                           network: pypsa.Network,
                           scenario,
                           year: str,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> pypsa.Network:
        """
        Ajoute les données temporelles au réseau.
        
        Args:
            network: Réseau PyPSA à compléter
            scenario: Scénario de simulation
            year: Année des données (ex: '2024')
            start_date: Date de début au format 'YYYY-MM-DD' (optionnel)
            end_date: Date de fin au format 'YYYY-MM-DD' (optionnel)
            
        Returns:
            pypsa.Network: Réseau avec les données temporelles ajoutées
        """
        # Définition des dates
        if year and not start_date:
            start_date = f"{year}-01-01"
        if year and not end_date:
            end_date = f"{year}-12-31"
            
        # Utiliser les dates du scénario si définies
        scenario_start = getattr(scenario, 'date_de_debut', start_date)
        scenario_end = getattr(scenario, 'date_de_fin', end_date)
        
        snapshots = pd.date_range(
            start=scenario.date_de_debut, 
            end=scenario.date_de_fin, 
            freq=scenario.pas_de_temps
        )
        network.set_snapshots(snapshots)
        
        p_max_pu_df, marginal_cost_df = await self.generate_timeseries(network, scenario)
        
        p_max_pu_df = p_max_pu_df.astype('float64')
        marginal_cost_df = marginal_cost_df.astype('float64')
        
        # Mise à jour des p_max_pu
        if year and hasattr(network.generators_t, 'p_max_pu') and network.generators_t.p_max_pu is not None:
            existing_cols = network.generators_t.p_max_pu.columns
            p_max_pu_df = pd.concat([
                network.generators_t.p_max_pu.drop(columns=p_max_pu_df.columns, errors='ignore'),
                p_max_pu_df
            ], axis=1).astype('float64') 
        
        # Mise à jour des données temporelles
        network.generators_t.p_max_pu = p_max_pu_df
        
        # Mise à jour des coûts marginaux variables
        if not hasattr(network.generators_t, 'marginal_cost'):
            network.generators_t.marginal_cost = pd.DataFrame(index=network.snapshots, dtype='float64')
        
        generators_list = list(network.generators.index)
        for col in list(marginal_cost_df.columns):
            if col not in generators_list:
                marginal_cost_df = marginal_cost_df.drop(columns=[col])
                
        # Ajouter tout générateur manquant avec une valeur par défaut
        for gen in generators_list:
            if gen not in marginal_cost_df.columns:
                default_cost = network.generators.at[gen, 'marginal_cost'] if 'marginal_cost' in network.generators.columns else 10.0
                marginal_cost_df[gen] = float(default_cost)
                
        network.generators_t.marginal_cost = marginal_cost_df
        
        # Chargement des demandes énergétiques
        load_demand_df = await self.load_demand_data(network, scenario, start_date, end_date)
        
        if not load_demand_df.empty:
            # Convertir l'index en DatetimeIndex si nécessaire
            if not isinstance(load_demand_df.index, pd.DatetimeIndex):
                load_demand_df.index = pd.to_datetime(load_demand_df.index)
            
            load_demand_df = load_demand_df.astype('float64')
            network.loads_t.p_set = load_demand_df
        
        return network

    async def fill_non_pilotable(self, network: pypsa.Network, source_type: str) -> pypsa.Network:
        """
        Remplit les données pour les générateurs non pilotables.
        
        Args:
            network: Le réseau PyPSA à compléter
            source_type: Type de source ('eolienne', 'solaire', 'hydro_fil', 'nucleaire')
            
        Returns:
            pypsa.Network: Réseau avec les générateurs ajoutés
        """
        db = next(get_db())
        geo_utils = GeoUtils()
        
        # Sélection des données selon le type de source
        if source_type == "eolienne":
            if self.eolienne_ids:
                centrales = await read_multiple_by_id(db, EolienneParc, self.eolienne_ids)
            else:
                centrales = await read_all_data(db, EolienneParc)
            df = pd.DataFrame([c.__dict__ for c in centrales])
            if not df.empty:
                # Mapping des colonnes pour éoliennes
                df['name'] = df['nom']
                df['p_nom'] = (df['puissance_nominal'] * df['nombre_eoliennes']) * 1e-3  # MW
                df['carrier'] = 'eolien'

        elif source_type == "solaire":
            if self.solaire_ids:
                centrales = await read_multiple_by_id(db, Solaire, self.solaire_ids)
            else:
                centrales = await read_all_data(db, Solaire)
            df = pd.DataFrame([c.__dict__ for c in centrales])
            if not df.empty:
                # Mapping des colonnes pour solaire
                df['name'] = df['nom']
                df['p_nom'] = df['puissance_nominal'] # Déjà en MW
                df['carrier'] = 'solaire'

        elif source_type == "hydro_fil":
            if self.hydro_ids:
                centrales = await read_multiple_by_id(db, Hydro, self.hydro_ids)
            else:
                centrales = await read_all_data(db, Hydro)
            df = pd.DataFrame([c.__dict__ for c in centrales])
            if not df.empty:
                df = df[df['type_barrage'] == "Fil de l'eau"]
                df['name'] = df['nom']
                df['p_nom'] = df['puissance_nominal']
                df['carrier'] = 'hydro_fil'

        elif source_type == "nucleaire":
            if self.nucleaire_ids:
                centrales = await read_multiple_by_id(db, Nucleaire, self.nucleaire_ids)
            else:
                centrales = await read_all_data(db, Nucleaire)
            df = pd.DataFrame([c.__dict__ for c in centrales])
            if not df.empty:
                df['name'] = df['centrale_nucleaire_nom']
                df['p_nom'] = df['puissance_nominal'] * 1e-3  # MW
                df['carrier'] = 'nucléaire'
        else:
            raise DataLoadError(f"Type de centrale non pris en charge: {source_type}")
            
        if not df.empty:
            df = df.drop(columns=['_sa_instance_state'], errors='ignore')
            
            generators_df = pd.DataFrame()
            generators_df['name'] = df['name'] 
            generators_df['bus'] = None  # Sera rempli par géolocalisation
            generators_df['type'] = 'non_pilotable'
            generators_df['p_nom'] = df['p_nom']
            generators_df['p_nom_extendable'] = False
            generators_df['p_nom_min'] = 0
            generators_df['carrier'] = df['carrier']
            generators_df['marginal_cost'] = 0.1
            
            # Trouver le bus le plus proche pour chaque centrale
            for idx, row in df.iterrows():
                if 'latitude' in df.columns and 'longitude' in df.columns:
                    point = (row['latitude'], row['longitude'])
                    nearest_bus, _ = geo_utils.find_nearest_bus(point, network)
                    generators_df.loc[idx, 'bus'] = nearest_bus
                    
                    # Mise à jour du type de bus si nécessaire
                    if nearest_bus is not None and nearest_bus in network.buses.index:
                        bus_type = network.buses.at[nearest_bus, 'type']
                        if ((isinstance(bus_type, str) and bus_type.lower() != 'prod') or 
                            (bus_type != BusType.prod)):
                            network.buses.at[nearest_bus, 'type'] = BusType.prod
            
            # Ajouter les générateurs au réseau
            for _, row in generators_df.iterrows():
                network.add("Generator", 
                           name=row['name'],
                           bus=row['bus'],
                           type=row['type'],
                           p_nom=row['p_nom'],
                           p_nom_extendable=row['p_nom_extendable'],
                           p_nom_min=row['p_nom_min'],
                           carrier=row['carrier'],
                           marginal_cost=row['marginal_cost'])
        
        return network
        
    async def fill_pilotable(self, network: pypsa.Network, source_type: str) -> pypsa.Network:
        """
        Remplit les données pour les générateurs pilotables.
        
        Args:
            network: Le réseau PyPSA à compléter
            source_type: Type de source ('hydro_reservoir' ou 'thermique')
            
        Returns:
            pypsa.Network: Réseau avec les générateurs ajoutés
        """
        db = next(get_db())
        geo_utils = GeoUtils()
        
        if source_type == "hydro_reservoir":
            if self.hydro_ids:
                centrales = await read_multiple_by_id(db, Hydro, self.hydro_ids)
            else:
                centrales = await read_all_data(db, Hydro)
            df = pd.DataFrame([c.__dict__ for c in centrales])
            if not df.empty:
                df = df[df['type_barrage'] == "Reservoir"]
                df['name'] = df['nom']
                df['p_nom'] = df['puissance_nominal']
                df['carrier'] = 'hydro_reservoir'

        elif source_type == "thermique":
            if self.thermique_ids:
                centrales = await read_multiple_by_id(db, Thermique, self.thermique_ids)
            else:
                centrales = await read_all_data(db, Thermique)
            df = pd.DataFrame([c.__dict__ for c in centrales])
            if not df.empty:
                df['name'] = df['nom']
                df['p_nom'] = df['puissance_nominal'] * 1e-3  # MW
                df['carrier'] = 'thermique'
        else:
            raise DataLoadError(f"Type de centrale pilotable non pris en charge: {source_type}")
            
        if not df.empty:
            df = df.drop(columns=['_sa_instance_state'], errors='ignore')
            
            generators_df = pd.DataFrame()
            generators_df['name'] = df['name'] 
            generators_df['bus'] = None  # Sera rempli par géolocalisation
            generators_df['type'] = 'pilotable'
            generators_df['p_nom'] = df['p_nom']
            generators_df['p_nom_extendable'] = True
            generators_df['p_nom_min'] = 0
            generators_df['p_nom_max'] = df['p_nom'] * 1.1  # 110% de capacité
            generators_df['p_max_pu'] = 1.0
            generators_df['carrier'] = df['carrier']
            
            # Trouver le bus le plus proche pour chaque centrale
            for idx, row in df.iterrows():
                if 'latitude' in df.columns and 'longitude' in df.columns:
                    point = (row['latitude'], row['longitude'])
                    nearest_bus, _ = geo_utils.find_nearest_bus(point, network)
                    generators_df.loc[idx, 'bus'] = nearest_bus
                    
                    # Mise à jour du type de bus si nécessaire
                    if nearest_bus is not None and nearest_bus in network.buses.index:
                        bus_type = network.buses.at[nearest_bus, 'type']
                        if ((isinstance(bus_type, str) and bus_type.lower() != 'prod') or 
                            (bus_type != BusType.prod)):
                            network.buses.at[nearest_bus, 'type'] = BusType.prod
            
            # Ajouter les générateurs au réseau
            for _, row in generators_df.iterrows():
                network.add("Generator", 
                           name=row['name'],
                           bus=row['bus'],
                           type=row['type'],
                           p_nom=row['p_nom'],
                           p_nom_extendable=row['p_nom_extendable'],
                           p_nom_min=row['p_nom_min'],
                           p_nom_max=row['p_nom_max'],
                           p_max_pu=row['p_max_pu'],
                           carrier=row['carrier'])
        
        return network
        
    async def generate_timeseries(self, network: pypsa.Network, scenario) -> tuple:
        """
        Génère les données temporelles pour tous les générateurs.
        
        Args:
            network: Le réseau PyPSA
            scenario: Scénario de simulation
            
        Returns:
            Tuple contenant:
                - DataFrame: p_max_pu pour chaque générateur
                - DataFrame: coûts marginaux pour chaque générateur
        """
        db = next(get_db())
        timestamps = pd.date_range(
            start=scenario.date_de_debut,
            end=scenario.date_de_fin,
            freq=scenario.pas_de_temps
        )
        month_indices = pd.DatetimeIndex(timestamps).month
        hour_indices = pd.DatetimeIndex(timestamps).hour
        p_max_pu_df = pd.DataFrame(index=timestamps)
        marginal_cost_df = pd.DataFrame(index=timestamps)
        
        
        # Génération pour les parcs solaires
        if self.solaire_ids:
            solaires = await read_multiple_by_id(db, Solaire, self.solaire_ids)
            
            for idx, parc in enumerate(solaires):
                infraSolaire = InfraSolaire(parc)
                infraSolaire.charger_scenario(scenario)
                production_df = infraSolaire.calculer_production()
                
                if production_df is not None:
                    nom = parc.nom
                    if nom in network.generators.index:
                        if 'production_horaire_wh' in production_df.columns:
                            # Calculer p_max_pu pour chaque heure = production_horaire_wh / (puissance_nominale * 1e6)
                            p_nom = parc.puissance_nominal * 1e6  # Conversion de MW à W
                            
                            p_values = production_df['production_horaire_wh'].values
                            hourly_index = production_df.index if 'datetime' not in production_df.columns else pd.to_datetime(production_df['datetime'])
                            hourly_production = pd.Series(p_values, index=hourly_index)
                            
                            aligned_production = hourly_production.reindex(network.snapshots).fillna(0)
                            
                            # Calculer p_max_pu = production_horaire / puissance_nominale
                            p_max_pu_df[nom] = aligned_production / p_nom
                            p_max_pu_df[nom] = p_max_pu_df[nom].fillna(0.1)  # Remplacer NaN par 0
        
        # Génération pour les centrales nucléaires
        if self.nucleaire_ids:
            nucleaires = await read_multiple_by_id(db, Nucleaire, self.nucleaire_ids)
            
            for idx, centrale in enumerate(nucleaires):
                infraNucleaire = InfraNucleaire(centrale)
                infraNucleaire.charger_scenario(scenario)
                production_df = infraNucleaire.calculer_production()
                
                if production_df is not None:
                    nom = centrale.centrale_nucleaire_nom
                    if nom in network.generators.index:
                        # Vérifier si on a des données horaires
                        if 'production_horaire_wh' in production_df.columns:
                            # Calculer p_max_pu pour chaque heure = production_horaire_wh / (puissance_nominale * 1e6)
                            p_nom = centrale.puissance_nominal  # Déjà en W
                            
                            p_values = production_df['production_horaire_wh'].values
                            hourly_index = production_df.index if 'datetime' not in production_df.columns else pd.to_datetime(production_df['datetime'])
                            hourly_production = pd.Series(p_values, index=hourly_index)
                            
                            aligned_production = hourly_production.reindex(network.snapshots).fillna(0)
                            
                            # Calculer p_max_pu = production_horaire / puissance_nominale
                            p_max_pu_df[nom] = aligned_production / p_nom
                            p_max_pu_df[nom] = p_max_pu_df[nom].fillna(0.85)

        # Génération pour les parcs éoliens
        if self.eolienne_ids:
            eoliennes = await read_multiple_by_id(db, EolienneParc, self.eolienne_ids)
            
            for parc in eoliennes:
                infraEolienne = InfraParcEolienne(parc)
                await infraEolienne.charger_scenario(scenario)
                production_iteration = infraEolienne.calculer_production()
                
                if production_iteration is not None and not production_iteration.empty:
                    nom = parc.nom
                    if nom in network.generators.index:
                        # Calcul du p_max_pu = production / puissance_nominale
                        p_nom = (parc.puissance_nominal * parc.nombre_eoliennes)
                        if 'puissance' in production_iteration.columns:
                            p_max_pu_df[nom] = production_iteration['puissance'] / p_nom
                            p_max_pu_df[nom] = p_max_pu_df[nom].fillna(0.25)
        
        marginal_cost_defaults = {
            'hydro_fil': 0.1,      # Faible coût - priorité haute
            'solaire': 0.1,        # Faible coût - priorité haute 
            'eolien': 0.1,         # Faible coût - priorité haute
            'nucléaire': 0.2,      # Coût très légèrement plus élevé
            'hydro_reservoir': 7.0, # Coût de base pour les réservoirs (sera dynamique)
            'thermique': 30.0,     # Coût élevé - basse priorité
            'emergency': 800.0,    # Très coûteux - dernier recours
            'slack': 900.0,        # Extrêmement coûteux - vraiment dernier recours
            'import': 0.5          # Coût moyen - priorité intermédiaire
        }
        
        # Appliquer les coûts marginaux par défaut 
        for gen_name, gen in network.generators.iterrows():
            carrier = gen.carrier if 'carrier' in gen.index else 'unknown'

            if carrier in marginal_cost_defaults:
                default_cost = marginal_cost_defaults[carrier]
                network.generators.at[gen_name, 'marginal_cost'] = default_cost            
            # Pour le coût marginal temporel
            if carrier in marginal_cost_defaults:
                # Pour les réservoirs, on utilise un modèle complexe plus tard
                marginal_cost_df[gen_name] = marginal_cost_defaults[carrier]
            else:
                marginal_cost_df[gen_name] = gen.marginal_cost if hasattr(gen, 'marginal_cost') else 10.0
            
            if gen_name not in p_max_pu_df.columns:
                # Générer des séries temporelles adaptées au type d'énergie
                    
                if carrier == 'hydro_fil':
                    seasonal = 0.7 + 0.3 * np.sin(np.pi * (month_indices - 3) / 6)
                    noise = 0.1 * np.random.normal(0, 1, len(timestamps))
                    profile = np.clip(seasonal + noise, 0.5, 1.0)
                    p_max_pu_df[gen_name] = profile
                    
                elif carrier == 'hydro_reservoir':
                    p_max_pu_df[gen_name] = 0.95 + 0.05 * np.random.random(len(timestamps))
                    
                elif carrier == 'thermique':
                    p_max_pu_df[gen_name] = 0.90 + 0.05 * np.random.random(len(timestamps))
                    
                    
                else:
                    # Valeur par défaut pour les autres types
                    p_max_pu_df[gen_name] = 1.0
        
        p_max_pu_df = p_max_pu_df.astype('float64')
        marginal_cost_df = marginal_cost_df.astype('float64')
        
        logger.info(f"Profils temporels générés pour {len(p_max_pu_df.columns)} générateurs")
        logger.info(f"Coûts marginaux générés pour {len(marginal_cost_df.columns)} générateurs")
        
        return p_max_pu_df, marginal_cost_df

    async def load_demand_data(self, network: pypsa.Network, scenario, start_date=None, end_date=None) -> pd.DataFrame:
        """
        Charge et distribue les données de demande énergétique.
        
        Cette méthode:
        1. Charge les données brutes depuis la DB (en kWh)
        2. Convertit les kWh en MW 
        3. Somme les demandes pour tous les secteurs à chaque heure
        4. Applique un facteur de mise à l'échelle pour atteindre la demande cible (~260 TWh)
        5. Distribue la demande entre les différentes charges du réseau
        
        Args:
            network: Le réseau PyPSA
            scenario: Scénario de simulation
            start_date: Date de début pour filtrer les données (optionnel)
            end_date: Date de fin pour filtrer les données (optionnel)
            
        Returns:
            pd.DataFrame: Demande distribuée pour chaque charge du réseau
        """
        scenario_year = None
        if hasattr(scenario, 'date_de_debut') and scenario.date_de_debut:
            scenario_year = str(pd.to_datetime(scenario.date_de_debut).year)
        
        # Définir les dates par défaut si nécessaire
        if not start_date and scenario_year:
            start_date = f"{scenario_year}-01-01"
        if not end_date and scenario_year:
            end_date = f"{scenario_year}-12-31"
            
        loads = network.loads.index
        n_loads = len(loads)
        
        if n_loads == 0:
            return pd.DataFrame()
            
        # Vérifier si une version en cache existe
        cache_key = f"demand_{scenario_year}_{start_date}_{end_date}_loads{n_loads}"
        cache_hash = hashlib.md5(cache_key.encode()).hexdigest()[:12]
        cache_file = DEMAND_CACHE_DIR / f"demand_{scenario_year}_{cache_hash}.parquet"
        
        if cache_file.exists() and scenario_year in ['2035', '2050']:
            try:
                logger.info(f"Chargement de la demande depuis le cache: {cache_file}")
                load_demand_df = pd.read_parquet(cache_file)
                
                if set(load_demand_df.columns) == set(loads):
                    return load_demand_df
                else:
                    logger.warning("Cache de demande invalide: les charges ne correspondent pas")
            except Exception as e:
                logger.warning(f"Erreur lors du chargement du cache de demande: {e}")
        
        # Si pas de cache valide, calculer la demande
        db_scenario = Scenario(
            weather=getattr(scenario, 'weather', 1),
            consomation=getattr(scenario, 'consomation', 1),
            date_de_debut=start_date or getattr(scenario, 'date_de_debut', None),
            date_de_fin=end_date or getattr(scenario, 'date_de_fin', None)
        )
        
        # Charger la demande totale
        demand_df = await read_demande_data(db_scenario, CUID=1)
        logger.info(f"Données de demande chargées: {len(demand_df)} lignes")
        
        # Convertir les dates en datetime
        if 'date' in demand_df.columns:
            demand_df['date'] = pd.to_datetime(demand_df['date'])
        
        # 1. Convertir les kWh en MW
        if 'electricity' in demand_df.columns:
            demand_df['electricity'] /= 1000
        
        if 'gaz' in demand_df.columns:
            demand_df['gaz'] /= 1000
        
        # 2. Groupement par secteur
        if 'sector' in demand_df.columns:
            demand_df = demand_df.groupby('date').sum(numeric_only=True).reset_index()
        else:
            # Vérifier les dates dupliquées
            date_counts = demand_df['date'].value_counts()
            if (date_counts > 1).any():
                demand_df = demand_df.groupby('date').sum(numeric_only=True).reset_index()

        # 3. Filtrer par année
        if scenario_year:
            year_filter = pd.to_datetime(demand_df['date']).dt.year == int(scenario_year)
            if year_filter.any():
                demand_df = demand_df[year_filter]
        
        # 4. Calculer la demande totale
        if 'electricity' in demand_df.columns and 'gaz' in demand_df.columns:
            demand_df['total_demand'] = demand_df['electricity'] + demand_df['gaz']
        elif 'electricity' in demand_df.columns:
            demand_df['total_demand'] = demand_df['electricity']
        else:
            demand_df['total_demand'] = 20000  # Valeur par défaut
        
        # 5. Appliquer un facteur d'échelle si nécessaire
        avg_demand = demand_df['total_demand'].mean()
        annual_energy_twh = avg_demand * 8760 / 1e6
        
        # Définir les cibles en fonction de l'année
            
        if scenario_year == "2050":
            target_energy_twh = 375.0
            target_avg_demand = 43000.0
            logger.info(f"Année 2050 détectée: cible de consommation à {target_energy_twh} TWh")
        else:  # 2035 ou autres années
            target_energy_twh = 260.0
            target_avg_demand = 30000.0
            logger.info(f"Année {scenario_year or 'inconnue'} détectée: cible de consommation à {target_energy_twh} TWh")
        
        if abs(annual_energy_twh - target_energy_twh) > 50:
            correction_factor = target_avg_demand / avg_demand
            logger.info(f"Application d'un facteur d'échelle: {correction_factor:.2f}x pour atteindre ~{target_energy_twh:.1f} TWh")
            demand_df['total_demand'] *= correction_factor
        
        demand_df = demand_df.set_index('date')
        demand_df.index = pd.to_datetime(demand_df.index)
        load_demand_df = pd.DataFrame(index=demand_df.index, columns=loads)
        np.random.seed(42)
        
        # Assigner des catégories pour les différentes charges
        load_categories = {}
        for load in loads:
            category = np.random.choice(['small', 'medium', 'large', 'xlarge'], 
                                       p=[0.4, 0.3, 0.2, 0.1])
            load_categories[load] = category
        
        # Distribuer la demande entre les charges
        n_timestamps = len(demand_df)
        
        for t in range(n_timestamps):
            timestamp = demand_df.index[t]
            total_demand_val = demand_df.loc[timestamp, 'total_demand']
            
            # Normaliser en float
            if isinstance(total_demand_val, (pd.Series, np.ndarray)):
                total_demand = float(total_demand_val.iloc[0] if hasattr(total_demand_val, 'iloc') else total_demand_val[0])
            else:
                total_demand = float(total_demand_val)
            
            # Générer des poids aléatoires pour la distribution
            random_weights = np.zeros(n_loads)
            time_factor = 0.7 + 0.6 * np.sin(t / 20.0)
            
            for i, load in enumerate(loads):
                category = load_categories[load]
                
                if category == 'small':
                    base = np.random.beta(0.8, 4.0) * 0.5  
                elif category == 'medium':
                    base = 0.5 + np.random.beta(2.0, 2.0) * 1.5
                elif category == 'large':
                    base = 1.0 + np.random.gamma(2.0, 0.9)
                else:  # 'xlarge'
                    base = 3.0 + np.random.gamma(3.0, 1.2)
                
                time_specific = 0.6 + 0.8 * np.sin(t/10.0 + i*0.5)
                noise_factor = 0.7 + 0.6 * np.random.random()
                random_weights[i] = max(0.01, base * time_specific * noise_factor * time_factor)
            
            # Normaliser pour que la somme soit égale à la demande totale
            total_weights = np.sum(random_weights)
            normalized_weights = random_weights / total_weights * total_demand
            
            # Distribuer la demande selon les poids
            for i, load in enumerate(loads):
                load_demand_df.loc[timestamp, load] = normalized_weights[i]
        
        if len(network.snapshots) > 1:
            time_diff = network.snapshots[1] - network.snapshots[0]
            if time_diff >= pd.Timedelta(hours=23):
                load_demand_df._energy_not_power = True
                logger.info("Mode journalier détecté: données marquées comme ÉNERGIE (MWh/jour)")
        
        # Sauvegarder dans le cache pour les années futures
        if scenario_year in ['2035', '2050']:
            try:
                logger.info(f"Sauvegarde de la demande dans le cache: {cache_file}")
                load_demand_df.to_parquet(cache_file)
            except Exception as e:
                logger.warning(f"Erreur lors de la sauvegarde du cache de demande: {e}")
        
        return load_demand_df


if __name__ == "__main__":
    from harmoniq.db.CRUD import read_data_by_id, read_all_scenario
    from harmoniq.db.engine import get_db
    from harmoniq.db.schemas import ListeInfrastructures
    import asyncio
    import time
    
    print("Testing load_demand_data functionality...")
    
    db = next(get_db())
    liste_infrastructures = asyncio.run(read_data_by_id(db, ListeInfrastructures, 1))
    scenario = read_all_scenario(db)[0]
    
    print(f"Using scenario: {scenario.nom} ({scenario.date_de_debut} to {scenario.date_de_fin})")
    
    loader = NetworkDataLoader()
    if hasattr(liste_infrastructures, 'parc_eoliens'):
        loader.set_infrastructure_ids(liste_infrastructures)
    network = asyncio.run(loader.load_network_data())
    print(f"Network has {len(network.buses)} buses, {len(network.loads)} loads")
    print("Generating randomized demand data...")
    start_time = time.time()
    load_demand_df = loader.load_demand_data(network, scenario)
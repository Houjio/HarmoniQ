"""
Module de chargement des données pour le réseau électrique.

Ce module gère le chargement des données statiques et temporelles 
du réseau électrique d'Hydro-Québec. Il prend en charge la lecture des fichiers CSV
pour la configuration du réseau et les séries temporelles de production/consommation.

Functions:
    load_network_data: Charge les données statiques du réseau.
    load_timeseries_data: Charge les données temporelles.

Classes:
    NetworkDataLoader: Classe principale pour le chargement des données.
    DataLoadError: Exception personnalisée pour les erreurs de chargement.

Example:
    >>> from network.utils import NetworkDataLoader
    >>> loader = NetworkDataLoader()
    >>> network_data = loader.load_network_data()
    >>> timeseries_data = loader.load_timeseries_data('2024')

Notes:
    Les données doivent suivre la structure suivante :
    - data/
        ├── regions/
        │   └── buses.csv         # Points de connexion du réseau
        │
        ├── topology/
        │   ├── lines/
        │   │   ├── line_types.csv    # Types de lignes standard
        │   │   └── lines.csv         # Lignes de transmission
        │   │
        │   ├── centrales/
        │   │    ├── carriers.csv      # Types de production
        │   │    ├── generators_non_pilotable.csv     # Caractéristiques des centrales non pilotables
        │   │    └── generators_pilotable.csv     # Caractéristiques des centrales pilotables
        │   │
        │   └── constraints/
        │        └── global_constraints.csv  # Contraintes globales
        │
        └── timeseries/
            └── 2024/
                ├── generation/
                │   ├── generators-p_max_pu.csv  # Production maximale par unité pour les centrales non pilotables
                │   └── generators-marginal_cost.csv # Coûts marginaux pour les centrales pilotables
                └── loads-p_set.csv              # Profils de charge

Contributeurs : Yanis Aksas (yanis.aksas@polymtl.ca)
                Add Contributor here
"""

import pypsa
import pandas as pd
from pathlib import Path
from typing import Optional
from .geo_utils import GeoUtils
from harmoniq.modules.eolienne import InfraParcEolienne

from harmoniq.db.engine import get_db
from harmoniq.db.schemas import Eolienne,Solaire,Hydro, Nucleaire, Thermique
from harmoniq.db.CRUD import (read_all_bus, read_all_line, read_all_line_type,
                              read_all_eolienne,read_all_solaire,read_all_hydro,
                              read_all_nucleaire,read_all_thermique,read_multiple_by_id)


class DataLoadError(Exception):
    """Exception levée lors d'erreurs de chargement des données."""
    pass


class NetworkDataLoader:
    """
    Gestionnaire de chargement des données du réseau.

    Cette classe utilise les fonctionnalités natives de PyPSA pour charger
    les données du réseau à partir des fichiers CSV.

    Attributes:
        data_dir (Path): Chemin vers le répertoire des données
    """

    def __init__(self, data_dir: str = "data"):
        """
        Initialise le chargeur de données.

        Args:
            data_dir: Chemin vers le répertoire des données.
                Defaults to "data".

        Raises:
            DataLoadError: Si le répertoire n'existe pas.
        """
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise DataLoadError(f"Le répertoire {data_dir} n'existe pas")
        
        self.eolienne_ids = None
        self.solaire_ids = None
        self.hydro_ids = None
        self.thermique_ids = None
        self.nucleaire_ids = None

    def set_infrastructure_ids(self, liste_infra):
        """
        Configure les IDs des infrastructures à charger à partir d'un objet liste_infrastructures.
        
        Args:
            liste_infra: Objet ListeInfrastructures contenant les IDs des infrastructures
        """
        if liste_infra.parc_eoliens:
            self.eolienne_ids = [int(id) for id in liste_infra.parc_eoliens.split(',')]
        
        if liste_infra.parc_solaires:
            self.solaire_ids = [int(id) for id in liste_infra.parc_solaires.split(',')]
        
        if liste_infra.central_hydroelectriques:
            self.hydro_ids = [int(id) for id in liste_infra.central_hydroelectriques.split(',')]
        
        if liste_infra.central_thermique:
            self.thermique_ids = [int(id) for id in liste_infra.central_thermique.split(',')]

    def load_network_data(self) -> pypsa.Network:
        """
        Charge les données statiques du réseau.

        Cette méthode charge la topologie du réseau (buses, lignes, générateurs)
        en utilisant la fonction native de PyPSA import_from_csv_folder.

        Returns:
            pypsa.Network: Réseau PyPSA configuré avec les données statiques.

        Raises:
            DataLoadError: Si les données sont inaccessibles ou mal formatées.
        """

        network = pypsa.Network()
        db = next(get_db())
        
        # Chargement des bus
        buses = read_all_bus(db)
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
        line_types = read_all_line_type(db)
        line_types_df = pd.DataFrame([lt.__dict__ for lt in line_types])
        if not line_types_df.empty:
            line_types_df = line_types_df.drop(columns=['_sa_instance_state'], errors='ignore')
            line_types_df = line_types_df.set_index('name')
            
            for idx, row in line_types_df.iterrows():
                network.add("LineType", name=idx, **row.to_dict())
        
        # Chargement des lignes
        lines = read_all_line(db)
        lines_df = pd.DataFrame([line.__dict__ for line in lines])
        if not lines_df.empty:
            lines_df = lines_df.drop(columns=['_sa_instance_state'], errors='ignore')
            lines_df = lines_df.set_index('name')
            
            for idx, row in lines_df.iterrows():
                network.add("Line", name=idx, **row.to_dict())

        # Chargement des générateurs 
        carriers_df = pd.read_csv(self.data_dir / "topology" / "centrales" / "carriers.csv")
        carriers_df = carriers_df.set_index('name')
        for idx, row in carriers_df.iterrows():
            network.add("Carrier", name=idx, **row.to_dict())

        # Chargement des générateurs non pilotables
        network = self.fill_non_pilotable(network, "eolienne")
        network = self.fill_non_pilotable(network, "solaire")
        network = self.fill_non_pilotable(network, "hydro_fil")
        network = self.fill_non_pilotable(network, "nucleaire")
        
        # Chargement des générateurs pilotables
        network = self.fill_pilotable(network, "hydro_reservoir")
        network = self.fill_pilotable(network, "thermique")
        
        # Chargement des contraintes
        global_constraints_df = pd.read_csv(
            self.data_dir / "topology" / "constraints" / "global_constraints.csv"
        ).set_index('name')
        for idx, row in global_constraints_df.iterrows():
            network.add("GlobalConstraint", name=idx, **row.to_dict())
            
        return network
            

    def load_timeseries_data(self, 
                           network: pypsa.Network,
                           scenario,
                           year: str,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> pypsa.Network:
        """
        Ajoute les données temporelles au réseau.

        Args:
            network: Réseau PyPSA à compléter avec les données temporelles
            year: Année des données (ex: '2024')
            start_date: Date de début au format 'YYYY-MM-DD' (optionnel)
            end_date: Date de fin au format 'YYYY-MM-DD' (optionnel)

        Returns:
            pypsa.Network: Réseau avec les données temporelles ajoutées

        Raises:
            DataLoadError: Si les données sont inaccessibles ou mal formatées
        """
        try:
            # Création de l'index temporel
            snapshots = pd.date_range(
                start=scenario.date_de_debut, 
                end=scenario.date_de_fin, 
                freq=scenario.pas_de_temps
            )
            network.set_snapshots(snapshots)
            
            if year:
                loads_path = self.data_dir / "timeseries" / year / "loads-p_set.csv"
                loads_df = pd.read_csv(loads_path, index_col=0, parse_dates=True)
                loads_df.columns = [f"load_{col}" for col in loads_df.columns]
                network.loads_t.p_set = loads_df
                
                gen_cost_path = self.data_dir / "timeseries" / year / "generation" / "generators-marginal_cost.csv"
                gen_cost_df = pd.read_csv(gen_cost_path, index_col=0, parse_dates=True)
                network.generators_t.marginal_cost = gen_cost_df
            
            p_max_pu_df = self.generate_non_pilotable_timeseries(network, scenario)
            
            if year and hasattr(network.generators_t, 'p_max_pu') and network.generators_t.p_max_pu is not None:
                existing_cols = network.generators_t.p_max_pu.columns
                p_max_pu_df = pd.concat([
                    network.generators_t.p_max_pu.drop(columns=p_max_pu_df.columns, errors='ignore'),
                    p_max_pu_df
                ], axis=1)
            
            # Mise à jour des données temporelles
            network.generators_t.p_max_pu = p_max_pu_df
            
            return network
            
        except Exception as e:
            raise DataLoadError(
                f"Erreur lors du chargement des données temporelles: {str(e)}"
            )       
    def fill_non_pilotable(self, network: pypsa.Network, source_type: str) -> pypsa.Network:
        """
        Remplit les données de production pour les générateurs non pilotables.
        
        Args:
            network: Le réseau PyPSA dans lequel ajouter les générateurs
            source_type: Le type de source d'énergie non pilotable ('eolienne' ou 'solaire')
            ids: Liste des IDs des centrales à inclure (si None, toutes seront incluses)
            
        Returns:
            pypsa.Network: Réseau avec les générateurs ajoutés
        """

        db = next(get_db())
        geo_utils = GeoUtils()
        
        if source_type == "eolienne":
            if self.eolienne_ids:
                centrales = read_multiple_by_id(db, Eolienne, self.eolienne_ids)
            else:
                centrales = read_all_eolienne(db)
            df = pd.DataFrame([c.__dict__ for c in centrales])
            if df.empty:
                return network
            
            else:
                # Mapping des colonnes pour éoliennes
                df['name'] = df['eolienne_nom']
                df['p_nom'] = df['puissance_nominal']
                df['carrier'] = 'eolien'

        elif source_type == "solaire":
            if self.solaire_ids:
                centrales = read_multiple_by_id(db, Solaire, self.solaire_ids)
            else:
                centrales = read_all_solaire(db)
            df = pd.DataFrame([c.__dict__ for c in centrales])
            if df.empty:
                return network
            
            else:
                # Mapping des colonnes pour solaire
                df['name'] = df['nom']
                df['p_nom'] = df['puissance_nominal']
                df['carrier'] = 'solaire'

        elif source_type == "hydro_fil":
            if self.hydro_ids:
                centrales = read_multiple_by_id(db, Hydro, self.hydro_ids)
            else:
                centrales = read_all_hydro(db)
            df = pd.DataFrame([c.__dict__ for c in centrales])
            if df.empty:
                return network
            
            else:
                df = df[df['type_barrage'] == "Fil de l'eau"]
                # Mapping des colonnes pour les barrages au fil de l'eau
                df['name'] = df['barrage_nom']
                df['p_nom'] = df['puissance_nominal']
                df['carrier'] = 'hydro_fil'

        elif source_type == "nucleaire":
            if self.nucleaire_ids:
                centrales = read_multiple_by_id(db, Nucleaire, self.nucleaire_ids)
            else:
                centrales = read_all_nucleaire(db)
            df = pd.DataFrame([c.__dict__ for c in centrales])
            if df.empty:
                return network
            
            else :
                # Mapping des colonnes pour nucléaires
                df['name'] = df['centrale_nucleaire_nom']
                df['p_nom'] = df['puissance_nominal']
                df['carrier'] = 'nucléaire'
        else:
            raise DataLoadError(f"Type de centrale non pris en charge: {source_type}")
            
        if not df.empty:
            df = df.drop(columns=['_sa_instance_state'], errors='ignore')
            
            # Création du DataFrame formaté pour PyPSA
            generators_df = pd.DataFrame()
            generators_df['name'] = df['name'] 
            generators_df['bus'] = None  # Sera rempli par la recherche du bus le plus proche
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
                        if bus_type != 'prod':
                            network.buses.at[nearest_bus, 'type'] = 'prod'
                            print(f"Bus {nearest_bus} mis à jour: type changé de '{bus_type}' à 'prod'")
            
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

        else:
            return network  # Aucune centrale trouvée
        
    def fill_pilotable(self, network: pypsa.Network, source_type: str) -> pypsa.Network:
        """
        Remplit les données de production pour les générateurs pilotables.
        
        Args:
            network: Le réseau PyPSA dans lequel ajouter les générateurs
            source_type: Le type de source d'énergie pilotable ('hydro_reservoir' ou 'thermique')
        Returns:
            pypsa.Network: Réseau avec les générateurs ajoutés
        """
        db = next(get_db())
        geo_utils = GeoUtils()
        
        if source_type == "hydro_reservoir":
            if self.hydro_ids:
                centrales = read_multiple_by_id(db, Hydro, self.hydro_ids)
            else:
                centrales = read_all_hydro(db)
            df = pd.DataFrame([c.__dict__ for c in centrales])
            if df.empty:
                return network
            
            else:
                df = df[df['type_barrage'] == "Reservoir"]
                # Mapping des colonnes pour les barrages à réservoir
                df['name'] = df['barrage_nom']
                df['p_nom'] = df['puissance_nominal']
                df['carrier'] = 'hydro_reservoir'

        elif source_type == "thermique":
            if self.thermique_ids:
                centrales = read_multiple_by_id(db, Thermique, self.thermique_ids)
            else:
                centrales = read_all_thermique(db)
            df = pd.DataFrame([c.__dict__ for c in centrales])
            if df.empty:
                return network
            
            else:
                # Mapping des colonnes pour thermiques
                df['name'] = df['nom']
                df['p_nom'] = df['puissance_nominal']
                df['carrier'] = 'thermique'
        else:
            raise DataLoadError(f"Type de centrale pilotable non pris en charge: {source_type}")
            
        if not df.empty:
            df = df.drop(columns=['_sa_instance_state'], errors='ignore')
            
            # Création du DataFrame formaté pour PyPSA
            generators_df = pd.DataFrame()
            generators_df['name'] = df['name'] 
            generators_df['bus'] = None  # Sera rempli par la recherche du bus le plus proche
            generators_df['type'] = 'pilotable'
            generators_df['p_nom'] = df['p_nom']
            generators_df['p_nom_extendable'] = True
            generators_df['p_nom_min'] = 0
            generators_df['p_nom_max'] = df['p_nom'] * 1.1  # 110% de la puissance nominale
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
                        if bus_type != 'prod':
                            network.buses.at[nearest_bus, 'type'] = 'prod'
                            print(f"Bus {nearest_bus} mis à jour: type changé de '{bus_type}' à 'prod'")
            
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

        else:
            return network  # Aucune centrale trouvée
        
    def generate_non_pilotable_timeseries(self, network: pypsa.Network, scenario) -> pd.DataFrame:
        """
        Génère les données temporelles pour les générateurs non pilotables en utilisant les modules
        de calcul spécifiques à chaque type d'énergie.
        
        Args:
            network: Le réseau PyPSA
            scenario: Le scénario contenant les paramètres de simulation
            
        Returns:
            pd.DataFrame: DataFrame contenant les p_max_pu pour chaque générateur non pilotable
        """
        db = next(get_db())
        p_max_pu_df = pd.DataFrame(index=pd.date_range(
            start=scenario.date_de_debut,
            end=scenario.date_de_fin,
            freq=scenario.pas_de_temps
        ))
        
        if self.eolienne_ids:
            eoliennes = read_multiple_by_id(db, Eolienne, self.eolienne_ids)
            if eoliennes:
                infra_eolienne = InfraParcEolienne(eoliennes)
                infra_eolienne.charger_scenario(scenario)
                production_df = infra_eolienne.calculer_production()
                production_df = production_df.fillna(0)
                
                for eolienne in eoliennes:
                    nom = eolienne.eolienne_nom
                    if nom in production_df.columns and nom in network.generators.index:
                        # Calcul du p_max_pu = production / puissance_nominale
                        p_nom = eolienne.puissance_nominal
                        p_max_pu_df[nom] = production_df[nom] / p_nom
                        print(f"Série temporelle générée pour l'éolienne {nom}")
        
        # TODO: Ajouter le code pour le solaire et l'hydro au fil de l'eau
        # Similaire à l'implémentation pour les éoliennes
        
        return p_max_pu_df
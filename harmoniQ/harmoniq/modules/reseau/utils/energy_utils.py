"""
Module d'utilitaires pour les calculs énergétiques du réseau.

Fournit des fonctionnalités pour la gestion des réservoirs, le calcul des coûts,
et l'estimation de la production d'énergie dans le réseau électrique.

Contributeurs : Yanis Aksas (yanis.aksas@polymtl.ca)
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
import logging
from harmoniq.db.engine import get_db
from harmoniq.db.CRUD import read_all_hydro
from harmoniq.modules.hydro.calcule import reservoir_infill
from pathlib import Path
import pypsa
import networkx as nx

logger = logging.getLogger("EnergyUtils")

class EnergyUtils:
    """
    Classe utilitaire pour les calculs énergétiques du réseau électrique.
    
    Fournit des méthodes pour la gestion des réservoirs, le calcul des coûts,
    et l'estimation de la production d'énergie.
    """
    
    @staticmethod
    def obtenir_energie_historique(annee: str, donnees_historiques=None) -> float:
        """
        Récupère l'énergie historique produite.
        
        Args:
            annee: Année des données historiques
            donnees_historiques: Données historiques optionnelles
            
        Returns:
            float: Énergie historique en MWh
        """
        energie_historique = {
            "2022": 210.8e6,  # TWh en MWh
            "2023": 205.2e6,
            "2024": 208.0e6 
        }
        
        if annee in energie_historique:
            return energie_historique[annee]
        
        return sum(energie_historique.values()) / len(energie_historique)
    
    @staticmethod
    def identifier_nouvelles_centrales(reseau, donnees_historiques=None) -> List:
        """
        Identifie les nouvelles centrales ajoutées.
        
        Args:
            reseau: Réseau PyPSA
            donnees_historiques: Données historiques optionnelles
            
        Returns:
            List: Nouvelles centrales identifiées
        """
        return []  # Simplifié pour l'instant
    
    @staticmethod
    def estimer_production_annuelle(centrale) -> float:
        """
        Estime la production annuelle d'une centrale.
        
        Args:
            centrale: Générateur PyPSA
            
        Returns:
            float: Production annuelle estimée en MWh
        """
        facteurs_capacite = {
            "hydro_fil": 0.5,
            "hydro_reservoir": 0.55,
            "eolien": 0.35,
            "solaire": 0.18,
            "thermique": 0.85,
            "nucléaire": 0.90
        }
        
        puissance_nominale = centrale.p_nom
        facteur = facteurs_capacite.get(centrale.carrier, 0.5)
        return puissance_nominale * facteur * 8760  # heures dans une année
    
    @staticmethod
    def obtenir_bus_frontiere(reseau, type_bus: str) -> str:
        """
        Obtient le bus frontière pour les interconnexions. Pour le moment, simplifié à un seul bus (Stanstead).
        
        Args:
            reseau: Réseau PyPSA
            type_bus: Type de bus recherché
            
        Returns:
            str: Identifiant du bus frontière
        """
        bus_interconnexion = "Stanstead"
        
        if bus_interconnexion in reseau.buses.index:
            return bus_interconnexion
        
        logger.warning(f"Bus {bus_interconnexion} non trouvé, utilisation du premier bus disponible")
        return reseau.buses.index[0]
    
    @staticmethod
    def get_niveau_reservoir(productions: pd.DataFrame, niveaux_actuels: dict, timestamp) -> pd.DataFrame:
        """
        Calcule les nouveaux niveaux de réservoir. (A vérifier, la fonction reservoir_infill a pas été testée)
        
        Args:
            productions: DataFrame contenant les productions pour chaque réservoir
            niveaux_actuels: Niveaux actuels de chaque réservoir (0-1)
            timestamp: Horodatage actuel
            
        Returns:
            pd.DataFrame: Nouveaux niveaux des réservoirs
        """
        db = next(get_db())
        barrages = read_all_hydro(db)
        
        CURRENT_DIR = Path(__file__).parent.parent.parent.parent / "modules" / "hydro"
        APPORT_DIR = CURRENT_DIR / "apport_naturel"
        
        date_jour = pd.Timestamp(timestamp.date())
        apport_naturel = pd.DataFrame(index=[timestamp])
        
        for barrage in barrages:
            if barrage.type_barrage == "Reservoir" and barrage.nom in productions.columns:
                try:
                    id_hq = str(barrage.id_HQ)
                    fichier_apport = APPORT_DIR / f"{id_hq}.csv"
                    
                    if fichier_apport.exists():
                        data_apport = pd.read_csv(fichier_apport)
                        data_apport["time"] = pd.to_datetime(data_apport["time"])
                        
                        jour_exact = data_apport[data_apport["time"].dt.date == date_jour.date()]
                        
                        if not jour_exact.empty:
                            apport_naturel[barrage.nom] = jour_exact["streamflow"].values[0]
                        else:
                            data_apport["diff"] = abs(data_apport["time"] - date_jour)
                            jour_proche = data_apport.loc[data_apport["diff"].idxmin()]
                            apport_naturel[barrage.nom] = jour_proche["streamflow"]
                    else:
                        apport_naturel[barrage.nom] = 15  # Valeur par défaut
                except Exception as e:
                    logger.error(f"Erreur chargement apports pour {barrage.nom}: {e}")
                    apport_naturel[barrage.nom] = 15

        niveaux_actuels_df = niveaux_actuels if isinstance(niveaux_actuels, pd.DataFrame) else pd.DataFrame([niveaux_actuels])
        
        return reservoir_infill(
            besoin_puissance=productions,
            pourcentage_reservoir=niveaux_actuels_df,
            apport_naturel=apport_naturel,
            timestamp=timestamp
        )
    
    @staticmethod
    def calcul_cout_reservoir(niveau: float) -> float:
        """
        Calcule le coût marginal en fonction du niveau du réservoir.
        
        Args:
            niveau: Niveau du réservoir (0-1)
            
        Returns:
            float: Coût marginal calculé
        """
        cout_minimum = 5
        cout_maximum = 35
        niveau_critique = 0.25
        
        niveau = max(0, min(1, niveau))
        
        if niveau < niveau_critique:
            # Croissance exponentielle en dessous du seuil critique
            facteur = (niveau_critique - niveau) / niveau_critique
            cout = cout_minimum + (cout_maximum - cout_minimum) * np.exp(2 * facteur) # Exponentielle plus douce
        else:
            # Décroissance linéaire au-dessus du seuil critique
            facteur = (1 - niveau) / (1 - niveau_critique)
            cout = cout_minimum + (cout_maximum/4 - cout_minimum) * facteur
        
        return round(cout, 2)
        
    @staticmethod
    def generer_faux_niveaux_reservoirs(snapshots, barrages_reservoir, seed=None):
        """
        Génère des niveaux de réservoirs simulés. Version simplifiée pour le temps de calcul.
        
        Args:
            snapshots: DatetimeIndex avec les pas de temps du scénario
            barrages_reservoir: Liste des noms des barrages à simuler
            seed: Graine pour la reproduction des résultats (optionnel)
            
        Returns:
            pd.DataFrame: Niveaux des réservoirs simulés (0-1)
        """
        if seed is not None:
            np.random.seed(seed)
        
        niveaux_df = pd.DataFrame(index=snapshots)
        
        for barrage in barrages_reservoir:
            # Niveau initial entre 0.4 et 0.8
            niveau_initial = np.random.uniform(0.4, 0.8)
            
            # Variations aléatoires et saisonnalité
            variations = np.random.normal(0, 0.01, size=len(snapshots))
            mois = pd.DatetimeIndex(snapshots).month
            saisonnalite = np.sin((mois - 3) * np.pi / 6) * 0.2  # Max en juin, min en décembre
            
            niveaux = niveau_initial + np.cumsum(variations)
            
            for i, timestamp in enumerate(snapshots):
                idx = min(i, len(saisonnalite)-1)
                niveaux[i] += saisonnalite[idx]
            
            niveaux_df[barrage] = np.clip(niveaux, 0.1, 1.0)
        
        return niveaux_df
    
    @staticmethod
    def ajouter_interconnexion_import_export(network, Pmax, bus_frontiere=None):
        """
        Ajoute une interconnexion d'import/export au réseau.
        
        Args:
            network: Réseau PyPSA
            Pmax: Capacité maximale d'import/export en MW
            bus_frontiere: Bus frontière (optionnel)
            
        Returns:
            pypsa.Network: Réseau mis à jour
        """
        if bus_frontiere is None:
            bus_frontiere = EnergyUtils.obtenir_bus_frontiere(network, "Interconnexion")
            
        if bus_frontiere not in network.buses.index:
            return network
            
        if Pmax >= 0:
            network.add(
                "Generator",
                f"import_{bus_frontiere}",
                bus=bus_frontiere,
                p_nom=Pmax,
                marginal_cost=0.5,
                carrier="import"
            )
        else:
            network.add(
                "Load",
                f"export_{bus_frontiere}",
                bus=bus_frontiere,
                p_set=0,
                carrier="export"
            )
            
            if not hasattr(network, 'loads_t'):
                network.loads_t = pypsa.descriptors.Dict({})
            if not hasattr(network.loads_t, 'p_max'):
                network.loads_t.p_max = pd.DataFrame(index=network.snapshots)
                
            network.loads_t.p_max[f"export_{bus_frontiere}"] = Pmax
        
        return network

    @staticmethod
    def reechantillonner_reseau_journalier(network):
        """
        Réechantillonne les données temporelles du réseau à une fréquence journalière.
        
        Cette méthode convertit les séries temporelles du réseau en données journalières:
        - Somme les consommations (loads) pour obtenir l'énergie totale par jour
        - Calcule la moyenne pour les autres séries temporelles
        
        Args:
            network: Réseau PyPSA à réechantillonner
            
        Returns:
            pypsa.Network: Réseau avec données temporelles réechantillonnées
        """
        if len(network.snapshots) <= 1:
            logger.warning("Pas assez de données temporelles pour réechantillonner")
            return network
        
        logger.info(f"Réechantillonnage de {len(network.snapshots)} pas de temps à fréquence journalière")
        
        new_network = pypsa.Network()
        
        # Liste des composants statiques
        component_types = [
            "buses", "carriers", "generators", "loads", "stores", "storage_units",
            "lines", "transformers", "links", "generator_t", "load_t", "line_types"
        ]
        
        for component_name in component_types:
            if hasattr(network, component_name):
                component_df = getattr(network, component_name)
                if isinstance(component_df, pd.DataFrame) and not component_df.empty:
                    setattr(new_network, component_name, component_df.copy())
        
        # Déterminer les snapshots journaliers (midi comme représentant)
        daily_snapshots = pd.DatetimeIndex([ts.replace(hour=12, minute=0, second=0) 
                                     for ts in pd.to_datetime(network.snapshots).floor('D').unique()])
        new_network.set_snapshots(daily_snapshots)
        
        for component_name in component_types:
            component_t_name = f"{component_name}_t"
            
            if not hasattr(network, component_t_name):
                continue
            
            component_t = getattr(network, component_t_name)
            
            # Pour les DataFrames simples
            if not isinstance(component_t, dict):
                if not isinstance(component_t, pd.DataFrame) or component_t.empty:
                    continue
                    
                df = component_t
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index)

                resampled_df = df.resample('D').sum() if component_name == "loads" else df.resample('D').mean()
                resampled_df.index = daily_snapshots[:len(resampled_df)]
                setattr(new_network, component_t_name, resampled_df)
                
            # Pour les dictionnaires de DataFrames
            else:
                for attr, df in component_t.items():
                    if df.empty:
                        continue
                    
                    if not isinstance(df.index, pd.DatetimeIndex):
                        df.index = pd.to_datetime(df.index)
                    
                    use_sum = component_name == "loads" and attr == "p_set"
                    resampled_df = df.resample('D').sum() if use_sum else df.resample('D').mean()
                    resampled_df.index = daily_snapshots[:len(resampled_df)]
                    
                    if use_sum:
                        resampled_df._energy_not_power = True
                        logger.info(f"Données de charge (p_set) marquées comme ÉNERGIE (MWh/jour) et non puissance (MW)")
                    
                    # Créer le dictionnaire si nécessaire
                    if not hasattr(new_network, component_t_name):
                        setattr(new_network, component_t_name, pypsa.descriptors.Dict({}))
                    
                    getattr(new_network, component_t_name)[attr] = resampled_df
        
        logger.info(f"Réechantillonnage terminé: {len(daily_snapshots)} jours")
        return new_network

    @staticmethod
    def ensure_network_solvability(network, reference_bus=None):
        """
        Assure la solvabilité du réseau en créant une topologie complètement connectée
        et en ajoutant suffisamment de capacité de génération si nécessaire.
        
        Cette méthode:
        1. Ajoute des lignes virtuelles pour connecter tous les composants
        2. Assure que chaque bus avec charge a accès à un générateur
        3. Vérifie que la capacité de génération est suffisante à chaque pas de temps
        
        Args:
            network: Réseau PyPSA à modifier
            reference_bus: Bus de référence pour les connexions (optionnel)
            
        Returns:
            pypsa.Network: Réseau modifié pour assurer la solvabilité
        """
        import networkx as nx
        import numpy as np

        EnergyUtils.align_time_indexes(network)

        G = nx.Graph()
        for bus in network.buses.index:
            G.add_node(bus)
            
        for _, line in network.lines.iterrows():
            G.add_edge(line.bus0, line.bus1)
        
        components = list(nx.connected_components(G))
        logger.info(f"Réseau avec {len(components)} composants non connectés")
        
        if reference_bus is None:
            buses_with_load = set(network.loads.bus)
            buses_with_gen = set(network.generators.bus)
            common_buses = buses_with_load.intersection(buses_with_gen)
            
            if common_buses:
                reference_bus = list(common_buses)[0]
            elif len(buses_with_gen) > 0:
                reference_bus = list(buses_with_gen)[0]
            else:
                reference_bus = network.buses.index[0]

        if "virtual_line_type" not in network.line_types.index:
            network.add(
                "LineType",
                "virtual_line_type",
                r=0.001,  
                x=0.01,
                b=0,   
                s_nom=1000000
            )
        
        if len(components) > 1:
            
            # Pour chaque composant, connecter un bus au bus de référence
            for i, comp in enumerate(components):
                if reference_bus in comp:
                    continue  # Sauter le composant qui contient déjà le bus de référence
                
                comp_bus = list(comp)[0]  # Premier bus du composant
                
                line_name = f"virtual_full_mesh_line_{i}"
                if line_name not in network.lines.index:
                    network.add(
                        "Line",
                        line_name,
                        bus0=reference_bus,
                        bus1=comp_bus,
                        type="virtual_line_type",
                        s_nom=1000000
                    )
        
        if hasattr(network.generators_t, 'p_max_pu'):
            # Pour chaque pas de temps, vérifier si la capacité est suffisante
            emergency_gens_data = {}            
            for timestamp in network.snapshots:
                try:
                    if timestamp in network.loads_t.p_set.index:
                        total_demand_t = network.loads_t.p_set.loc[timestamp].sum()
                    else:
                        if not network.loads_t.p_set.empty:
                            total_demand_t = network.loads_t.p_set.mean().sum()  # Moyenne comme valeur par défaut
                        else:
                            total_demand_t = 0  # Aucune demande si aucune donnée disponible
                    
                    available_capacity = 0
                    for gen in network.generators.index:
                        p_nom = network.generators.loc[gen, 'p_nom']
                        p_max_pu = 1.0  # Par défaut
                        
                        if gen in network.generators_t.p_max_pu.columns:
                            if timestamp in network.generators_t.p_max_pu.index:
                                p_max_pu = network.generators_t.p_max_pu.loc[timestamp, gen]
                        
                        available_capacity += p_nom * p_max_pu
                    
                    # Si la capacité est insuffisante, ajouter un générateur d'urgence
                    if available_capacity < total_demand_t:
                        capacity_gap = total_demand_t - available_capacity
                        gen_name = f"import_gen_{timestamp.strftime('%Y%m%d')}"
                        
                        if gen_name not in network.generators.index:
                            network.add(
                                "Generator",
                                gen_name,
                                bus=reference_bus,
                                p_nom=capacity_gap * 1.1,
                                marginal_cost=800,
                                carrier="import"
                            )

                        emergency_gens_data[gen_name] = 1.0
                        
                except KeyError as e:
                    logger.error(f"Erreur lors du traitement du timestamp {timestamp}: {str(e)}")
                    continue

            if emergency_gens_data:
                p_max_pu_copy = network.generators_t.p_max_pu.copy()
                for gen_name, value in emergency_gens_data.items():
                    if gen_name not in p_max_pu_copy.columns:
                        p_max_pu_copy[gen_name] = 0
                        
                    for ts in network.snapshots:
                        if gen_name.endswith(ts.strftime('%Y%m%d')):
                            p_max_pu_copy.at[ts, gen_name] = value
                network.generators_t.p_max_pu = p_max_pu_copy
        
        network.generators.p_nom_extendable = True
        network.generators.p_nom_max = network.generators.p_nom * 1.5 
        
        return network

    @staticmethod
    def align_time_indexes(network):
        """
        Aligne tous les index temporels du réseau avec les snapshots en cas d'incohérence dans les timestamps des différentes entrées.
        
        Cette méthode:
        1. Identifie tous les DataFrames temporels dans le réseau
        2. Réindexe tous ces DataFrames pour qu'ils correspondent aux snapshots
        3. Remplit les valeurs manquantes par des valeurs appropriées
        
        Args:
            network: Réseau PyPSA à traiter
        """
        logger.info("Alignement des index temporels avec les snapshots du réseau...")
        
        if not hasattr(network, 'snapshots') or len(network.snapshots) == 0:
            logger.warning("Pas de snapshots définis dans le réseau")
            return
        
        if hasattr(network, 'generators_t'):
            for attr_name, df in network.generators_t.items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    if not df.index.equals(network.snapshots):
                        
                        aligned_df = pd.DataFrame(index=network.snapshots, columns=df.columns)
                        
                        for col in df.columns:
                            # Pour les indices communs, prenons les valeurs existantes
                            common_idx = df.index.intersection(network.snapshots)
                            aligned_df.loc[common_idx, col] = df.loc[common_idx, col]
                            
                            # Pour les indices manquants, utiliser une stratégie de remplissage
                            missing_idx = network.snapshots.difference(df.index)
                            if not missing_idx.empty:
                                if not df.empty:
                                    last_val = df.loc[df.index[-1], col]
                                    aligned_df.loc[missing_idx, col] = last_val
                                else:
                                    default_val = 0.0
                                    if attr_name == 'p_max_pu':
                                        default_val = 0.9
                                    elif attr_name == 'marginal_cost':
                                        default_val = 10.0
                                    
                                    aligned_df.loc[missing_idx, col] = default_val

                        network.generators_t[attr_name] = aligned_df
        
        # Aligner les index temporels des charges
        if hasattr(network, 'loads_t'):
            for attr_name, df in network.loads_t.items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    if not df.index.equals(network.snapshots):
                        
                        aligned_df = pd.DataFrame(index=network.snapshots, columns=df.columns)

                        for col in df.columns:
                            common_idx = df.index.intersection(network.snapshots)
                            aligned_df.loc[common_idx, col] = df.loc[common_idx, col]

                            missing_idx = network.snapshots.difference(df.index)
                            if not missing_idx.empty:
                                if not df.empty:
                                    mean_val = df[col].mean()
                                    std_val = df[col].std() if len(df) > 1 else mean_val * 0.1
                                    
                                    for idx in missing_idx:
                                        prev_week = idx - pd.Timedelta(days=7)
                                        if prev_week in df.index:
                                            val = df.loc[prev_week, col]
                                        else:
                                            noise = np.random.normal(0, std_val * 0.1)
                                            val = max(0, mean_val + noise)
                                        
                                        aligned_df.loc[idx, col] = val
                                else:
                                    aligned_df.loc[missing_idx, col] = 0.0
                        
                        network.loads_t[attr_name] = aligned_df

    @staticmethod
    def calculate_energy_from_power(network, power_data, is_journalier=None):
        """
        Calcule l'énergie à partir des valeurs de puissance en tenant compte 
        de la durée des snapshots.
        
        Args:
            network: Réseau PyPSA contenant les snapshots
            power_data: DataFrame ou Series contenant des valeurs de puissance en MW
            is_journalier: Si True, force le mode journalier (override de la détection auto)
            
        Returns:
            Même structure que power_data, mais avec des valeurs en MWh
        """
        daily_snapshots = False
        
        if is_journalier is not None:
            daily_snapshots = is_journalier
        elif len(network.snapshots) > 1:
            time_diff = network.snapshots[1] - network.snapshots[0]
            if time_diff >= pd.Timedelta(hours=23):
                daily_snapshots = True
        
        data_is_energy = getattr(power_data, '_energy_not_power', False)
        
        if isinstance(power_data, pd.DataFrame):
            energy_data = power_data.copy()
            
            if daily_snapshots and not data_is_energy:
                logger.info(f"Mode journalier: Conversion puissance (MW) → énergie (MWh/jour)")
                energy_data = energy_data * 24
            
        elif isinstance(power_data, pd.Series):
            energy_data = power_data.copy()
            
            if daily_snapshots and not data_is_energy:
                energy_data = energy_data * 24
        
        else:
            energy_data = power_data
            if daily_snapshots and not data_is_energy:
                energy_data = energy_data * 24
        
        return energy_data

    @staticmethod
    def debug_network_energy_allocation(network, period='auto', is_journalier=None):
        """
        Affiche des informations détaillées sur l'allocation d'énergie dans le réseau.
        
        Args:
            network: Le réseau PyPSA à analyser
            period: 'daily', 'hourly', ou 'auto' pour détection automatique
            is_journalier: Si True, force le mode journalier (override du paramètre period)
        """
        
        hours_per_snapshot = 1 
        
        if is_journalier is not None:
            if is_journalier:
                hours_per_snapshot = 24
                period = 'daily'
            else:
                hours_per_snapshot = 1
                period = 'hourly'
            logger.info(f"Mode {'journalier' if is_journalier else 'horaire'} ")
        elif period == 'auto':
            if len(network.snapshots) > 1:
                time_diff = network.snapshots[1] - network.snapshots[0]
                if time_diff >= pd.Timedelta(hours=23):
                    hours_per_snapshot = 24
                    period = 'daily'
                    logger.info(f"Mode journalier détecté automatiquement (écart: {time_diff})")
                else:
                    hours_per_snapshot = 1
                    period = 'hourly'
                    logger.info(f"Mode horaire détecté automatiquement (écart: {time_diff})")
        else:
            hours_per_snapshot = 24 if period == 'daily' else 1
        
        # Facteur de conversion puissance → énergie
        hours_per_snapshot = 24 if period == 'daily' else 1
        
        carriers = network.generators.carrier.unique()
        
        total_power = network.generators_t['p'].sum().sum()
        total_energy = total_power * hours_per_snapshot
        
        logger.info(f"Analyse détaillée de l'allocation d'énergie:")
        logger.info(f"Snapshots: {len(network.snapshots)} ({period})")
        
        if period == 'daily':
            logger.info(f"Puissance moyenne journalière: {total_power/len(network.snapshots):.2f} MW")
            logger.info(f"Puissance totale cumulée: {total_power:.2f} MW")
            logger.info(f"Énergie journalière moyenne: {total_energy/len(network.snapshots):.2f} MWh/jour")
            logger.info(f"Énergie totale: {total_energy:.2f} MWh ({total_energy/1e6:.2f} TWh)")
        else:
            logger.info(f"Puissance moyenne: {total_power/len(network.snapshots):.2f} MW")  
            logger.info(f"Puissance totale cumulée: {total_power:.2f} MW")
            logger.info(f"Énergie totale: {total_energy:.2f} MWh ({total_energy/1e6:.2f} TWh)")
        
        for carrier in carriers:
            carrier_gens = network.generators[network.generators.carrier == carrier].index
            if len(carrier_gens) > 0:
                # Capacité installée
                capacity = network.generators[network.generators.carrier == carrier].p_nom.sum()
                
                # Production totale
                carrier_power = network.generators_t['p'][carrier_gens].sum().sum()
                carrier_energy = carrier_power * hours_per_snapshot
                
                # Facteur de capacité moyen
                if capacity > 0:
                    capacity_factor = carrier_power / (capacity * len(network.snapshots))
                else:
                    capacity_factor = 0
                
                # Pourcentage du mix
                percentage = 100 * carrier_power / total_power if total_power > 0 else 0
                
                logger.info(f"  {carrier}:")
                logger.info(f"    - Capacité installée: {capacity:.2f} MW")
                logger.info(f"    - Puissance produite: {carrier_power:.2f} MW ({percentage:.1f}%)")
                logger.info(f"    - Énergie produite: {carrier_energy:.2f} MWh")
                logger.info(f"    - Facteur de capacité: {capacity_factor*100:.1f}%")
                
                # Contrainte d'accès aux données?
                if carrier_power == 0 and capacity > 0:
                    logger.warning(f"{carrier} a une capacité de {capacity:.2f} MW mais produit 0 MW")
                    
                    # Vérifier si les générateurs ont des données p_max_pu disponibles
                    if hasattr(network.generators_t, 'p_max_pu'):
                        p_max_pu_available = sum(1 for gen in carrier_gens if gen in network.generators_t.p_max_pu.columns)
                        if p_max_pu_available < len(carrier_gens):
                            logger.warning(f"Seulement {p_max_pu_available}/{len(carrier_gens)} générateurs ont des données p_max_pu")
                    
                    # Vérifier les coûts marginaux
                    if hasattr(network.generators_t, 'marginal_cost'):
                        for gen in carrier_gens:
                            if gen in network.generators_t.marginal_cost.columns:
                                cost_min = network.generators_t.marginal_cost[gen].min()
                                cost_max = network.generators_t.marginal_cost[gen].max()
                                logger.info(f"    - Coût marginal pour {gen}: {cost_min:.2f}-{cost_max:.2f}")
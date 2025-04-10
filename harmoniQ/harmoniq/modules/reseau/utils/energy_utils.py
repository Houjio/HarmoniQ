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
        Obtient le bus frontière pour les interconnexions.
        
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
        Calcule les nouveaux niveaux de réservoir.
        
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
        cout_minimum = 5     # Coût quand le réservoir est plein
        cout_maximum = 35    # Coût quand le réservoir est presque vide (modifié de 150 à 35)
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
        Génère des niveaux de réservoirs simulés.
        
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
                    
                    # Somme pour les consommations (p_set), moyenne pour le reste
                    use_sum = component_name == "loads" and attr == "p_set"
                    resampled_df = df.resample('D').sum() if use_sum else df.resample('D').mean()
                    resampled_df.index = daily_snapshots[:len(resampled_df)]
                    
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
        et en ajoutant suffisamment de capacité de génération.
        
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
        
        # Assurer que tous les DataFrames temporels ont les mêmes index que les snapshots du réseau
        EnergyUtils.align_time_indexes(network)
        
        # 1. Construire le graphe du réseau existant
        G = nx.Graph()
        for bus in network.buses.index:
            G.add_node(bus)
            
        for _, line in network.lines.iterrows():
            G.add_edge(line.bus0, line.bus1)
        
        components = list(nx.connected_components(G))
        logger.info(f"Réseau avec {len(components)} composants non connectés")
        
        if reference_bus is None:
            # Trouver un bus avec charge et générateur
            buses_with_load = set(network.loads.bus)
            buses_with_gen = set(network.generators.bus)
            common_buses = buses_with_load.intersection(buses_with_gen)
            
            if common_buses:
                reference_bus = list(common_buses)[0]
            elif len(buses_with_gen) > 0:
                reference_bus = list(buses_with_gen)[0]
            else:
                reference_bus = network.buses.index[0]
        
        
        # 2. Créer un type de ligne virtuelle à haute capacité
        if "virtual_line_type" not in network.line_types.index:
            network.add(
                "LineType",
                "virtual_line_type",
                r=0.001,   # Résistance très faible
                x=0.01,    # Réactance minimale 
                b=0,       # Susceptance nulle
                s_nom=1000000  # Capacité très élevée
            )
        
        # 3. Connecter tous les composants avec des lignes virtuelles
        if len(components) > 1:
            
            # Pour chaque composant, connecter un bus au bus de référence
            for i, comp in enumerate(components):
                if reference_bus in comp:
                    continue  # Sauter le composant qui contient déjà le bus de référence
                
                comp_bus = list(comp)[0]  # Premier bus du composant
                
                # Ajouter une ligne virtuelle
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
        
        # 5. Vérifier la capacité totale de génération à chaque pas de temps
        if hasattr(network.generators_t, 'p_max_pu'):
            # Pour chaque pas de temps, vérifier si la capacité est suffisante
            for timestamp in network.snapshots:
                # Vérifier si le timestamp existe dans p_set avant d'y accéder
                try:
                    if timestamp in network.loads_t.p_set.index:
                        total_demand_t = network.loads_t.p_set.loc[timestamp].sum()
                    else:
                        # Si le timestamp n'existe pas, utiliser la moyenne ou ignorer
                        logger.warning(f"Timestamp {timestamp} non trouvé dans network.loads_t.p_set. Utilisation de valeur par défaut.")
                        if not network.loads_t.p_set.empty:
                            total_demand_t = network.loads_t.p_set.mean().sum()  # Moyenne comme valeur par défaut
                        else:
                            total_demand_t = 0  # Aucune demande si aucune donnée disponible
                    
                    # Calculer la capacité de génération disponible
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
                        gen_name = f"emergency_gen_{timestamp.strftime('%Y%m%d')}"
                        
                        if gen_name not in network.generators.index:
                            network.add(
                                "Generator",
                                gen_name,
                                bus=reference_bus,
                                p_nom=capacity_gap * 1.1,  # 10% de marge
                                marginal_cost=800,  # Très coûteux
                                carrier="emergency"
                            )
                            logger.info(f"Générateur d'urgence ajouté pour {timestamp}: {capacity_gap:.2f} MW")
                        
                        # Assurer que le générateur est disponible pour ce pas de temps
                        if gen_name not in network.generators_t.p_max_pu.columns:
                            network.generators_t.p_max_pu[gen_name] = 0
                        
                        if timestamp in network.generators_t.p_max_pu.index:
                            network.generators_t.p_max_pu.at[timestamp, gen_name] = 1.0
                except KeyError as e:
                    logger.error(f"Erreur lors du traitement du timestamp {timestamp}: {str(e)}")
                    # Continuer avec le timestamp suivant
                    continue
        
        # 6. Créer une matrice "safety_factor" pour tous les générateurs
        network.generators.p_nom_extendable = True
        network.generators.p_nom_max = network.generators.p_nom * 1.5  # 50% de flexibilité 
        
        return network

    @staticmethod
    def align_time_indexes(network):
        """
        Aligne tous les index temporels du réseau avec les snapshots.
        
        Cette méthode:
        1. Identifie tous les DataFrames temporels dans le réseau
        2. Réindexe tous ces DataFrames pour qu'ils correspondent aux snapshots du réseau
        3. Remplit les valeurs manquantes par des valeurs appropriées (moyenne, valeur précédente, etc.)
        
        Args:
            network: Réseau PyPSA à traiter
        """
        logger.info("Alignement des index temporels avec les snapshots du réseau...")
        
        if not hasattr(network, 'snapshots') or len(network.snapshots) == 0:
            logger.warning("Pas de snapshots définis dans le réseau")
            return
        
        # Vérifier et aligner les index temporels des générateurs
        if hasattr(network, 'generators_t'):
            for attr_name, df in network.generators_t.items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    if not df.index.equals(network.snapshots):
                        logger.info(f"Réindexation de network.generators_t.{attr_name}")
                        
                        aligned_df = pd.DataFrame(index=network.snapshots, columns=df.columns)
                        
                        for col in df.columns:
                            # Pour les indices communs, prenons les valeurs existantes
                            common_idx = df.index.intersection(network.snapshots)
                            aligned_df.loc[common_idx, col] = df.loc[common_idx, col]
                            
                            # Pour les indices manquants, utilisons une stratégie de remplissage
                            missing_idx = network.snapshots.difference(df.index)
                            if not missing_idx.empty:
                                if not df.empty:
                                    last_val = df.loc[df.index[-1], col]
                                    aligned_df.loc[missing_idx, col] = last_val
                                # Générer des valeurs aléatoires basées sur la moyenne et l'écart-type
                                else:
                                    default_val = 0.0
                                    if attr_name == 'p_max_pu':
                                        default_val = 0.9  # Valeur par défaut pour p_max_pu
                                    elif attr_name == 'marginal_cost':
                                        default_val = 10.0  # Valeur par défaut pour marginal_cost
                                    
                                    aligned_df.loc[missing_idx, col] = default_val

                        network.generators_t[attr_name] = aligned_df
        
        # Vérifier et aligner les index temporels des charges
        if hasattr(network, 'loads_t'):
            for attr_name, df in network.loads_t.items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    if not df.index.equals(network.snapshots):
                        logger.info(f"Réindexation de network.loads_t.{attr_name}")
                        
                        aligned_df = pd.DataFrame(index=network.snapshots, columns=df.columns)

                        for col in df.columns:
                            common_idx = df.index.intersection(network.snapshots)
                            aligned_df.loc[common_idx, col] = df.loc[common_idx, col]

                            missing_idx = network.snapshots.difference(df.index)
                            if not missing_idx.empty:
                                if not df.empty:
                                    # Si nous avons un historique, utilisons la valeur du même jour de la semaine précédente
                                    # ou à défaut la moyenne avec un peu d'aléatoire
                                    mean_val = df[col].mean()
                                    std_val = df[col].std() if len(df) > 1 else mean_val * 0.1
                                    
                                    for idx in missing_idx:
                                        # Chercher une semaine avant
                                        prev_week = idx - pd.Timedelta(days=7)
                                        if prev_week in df.index:
                                            val = df.loc[prev_week, col]
                                        else:
                                            # Ajouter un peu d'aléatoire autour de la moyenne
                                            noise = np.random.normal(0, std_val * 0.1)
                                            val = max(0, mean_val + noise)
                                        
                                        aligned_df.loc[idx, col] = val
                                else:
                                    # Si nous n'avons aucune donnée, utiliser une valeur par défaut
                                    aligned_df.loc[missing_idx, col] = 0.0
                        
                        network.loads_t[attr_name] = aligned_df
        
        logger.info("Alignement des index temporels terminé")
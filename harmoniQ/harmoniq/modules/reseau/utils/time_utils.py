"""
Module utilitaire pour la gestion des séries temporelles.

Ce module fournit des fonctions supplémentaires pour manipuler et analyser
les données temporelles du réseau électrique d'Hydro-Québec.

Example:
    >>> from network.utils import TimeSeriesManager
    >>> manager = TimeSeriesManager()
    >>> peaks = manager.find_peak_demand(network, '2024-01')

Contributeurs : Yanis Aksas (yanis.aksas@polymtl.ca)
                Add Contributor here
"""

import pypsa
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime


class TimeSeriesManager:
    """
    Gestionnaire des séries temporelles du réseau.
    
    Cette classe fournit des méthodes d'analyse et de manipulation
    des données temporelles qui complètent les fonctionnalités de PyPSA.
    """

    @staticmethod
    def find_peak_demand(network: pypsa.Network, 
                        period: str = None) -> pd.Series:
        """
        Trouve les pics de demande sur le réseau.

        Args:
            network: Réseau PyPSA à analyser
            period: Période à analyser (format 'YYYY-MM' ou 'YYYY')

        Returns:
            Series avec les timestamps des pics et leurs valeurs
        """
        if period:
            loads = network.loads_t.p_set[network.loads_t.p_set.index.strftime('%Y-%m') == period]
        else:
            loads = network.loads_t.p_set

        total_load = loads.sum(axis=1)
        return total_load.nlargest(5)  # Retourne les 5 plus grands pics

    @staticmethod
    def get_seasonal_stats(network: pypsa.Network) -> Dict:
        """
        Calcule les statistiques par saison.

        Returns:
            Dict contenant les moyennes saisonnières de charge et production
        """
        # Ajoute la saison comme index
        loads = network.loads_t.p_set.copy()
        loads.index = pd.to_datetime(loads.index)
        loads['season'] = loads.index.quarter

        # Distingue les générateurs pilotables et non-pilotables
        non_pilotable_gens = network.generators[
            network.generators.carrier.isin(['hydro_fil', 'eolien', 'solaire'])
        ].index
        pilotable_gens = network.generators[
            network.generators.carrier.isin(['hydro_reservoir', 'thermique'])
        ].index

        # Calcule les moyennes par saison
        seasonal_means = {
            'load': loads.groupby('season').mean(),
            'non_pilotable_generation': network.generators_t.p_max_pu[non_pilotable_gens].groupby(
                pd.to_datetime(network.generators_t.p_max_pu.index).quarter
            ).mean(),
            'pilotable_marginal_cost': network.generators_t.marginal_cost[pilotable_gens].groupby(
                pd.to_datetime(network.generators_t.marginal_cost.index).quarter
            ).mean()
        }
        
        return seasonal_means

    @staticmethod
    def analyze_production_patterns(network: pypsa.Network, 
                                  carrier: str = None) -> pd.DataFrame:
        """
        Analyse les patterns de production par type de centrale.

        Args:
            network: Réseau PyPSA
            carrier: Type de production à analyser

        Returns:
            DataFrame avec les statistiques de production
        """
        production_stats = pd.DataFrame()
        
        if carrier:
            if carrier in ['hydro_fil', 'eolien', 'solaire']:
                gens = network.generators[network.generators.carrier == carrier].index
                data = network.generators_t.p_max_pu[gens]
            else:  # carriers pilotables
                gens = network.generators[network.generators.carrier == carrier].index
                data = network.generators_t.marginal_cost[gens]
        else:
            # Combine les deux types de données
            non_pilotable_data = network.generators_t.p_max_pu
            pilotable_data = network.generators_t.marginal_cost
            data = pd.concat([non_pilotable_data, pilotable_data], axis=1)

        # Ajout de colonnes temporelles pour l'analyse
        production_stats['hour'] = data.index.hour
        production_stats['month'] = data.index.month
        production_stats['weekday'] = data.index.weekday
        production_stats['value'] = data.mean(axis=1)

        return production_stats

    @staticmethod
    def check_temporal_consistency(network: pypsa.Network) -> bool:
        """
        Vérifie la cohérence temporelle des données.

        Returns:
            bool: True si toutes les séries temporelles sont cohérentes
        """
        # Récupère tous les timestamps
        load_times = set(network.loads_t.p_set.index)
        non_pilotable_times = set(network.generators_t.p_max_pu.index)
        pilotable_times = set(network.generators_t.marginal_cost.index)
        
        # Vérifie que tous les timestamps correspondent
        return load_times == non_pilotable_times == pilotable_times

    @staticmethod
    def get_time_resolution(network: pypsa.Network) -> str:
        """
        Détermine la résolution temporelle des données.

        Returns:
            str: Description de la résolution (ex: '1H' pour horaire)
        """
        if len(network.snapshots) < 2:
            return "N/A"
        
        diff = network.snapshots[1] - network.snapshots[0]
        return str(diff)
    
    # Add new method here
"""
Module principal pour la construction et l'analyse du réseau électrique.

Ce module orchestre la construction, l'optimisation et l'analyse du réseau
électrique d'Hydro-Québec en utilisant PyPSA. Il coordonne l'utilisation
des différents composants (chargement des données, optimisation, calculs 
de flux de puissance).

Example:
    >>> from network.core import NetworkBuilder
    >>> builder = NetworkBuilder()
    >>> network = builder.create_network("2024")
    >>> network = builder.optimize_network(network)
    >>> results = builder.analyze_results(network)

Contributeurs : Yanis Aksas (yanis.aksas@polymtl.ca)
                Add Contributor here
"""

import pypsa
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

from harmoniq.modules.reseau.utils import NetworkDataLoader
from .optimization import NetworkOptimizer
from .power_flow import PowerFlowAnalyzer


class NetworkBuilder:
    """
    Classe principale pour l'orchestration du modèle de réseau électrique.
    
    Cette classe coordonne les différentes étapes de la modélisation :
    - Construction du réseau à partir des données CSV
    - Optimisation de la production
    - Calculs de flux de puissance
    - Analyse des résultats

    Attributes:
        data_loader (NetworkDataLoader): Gestionnaire de chargement des données
        current_network (pypsa.Network): Réseau PyPSA en cours d'analyse
    """

    def __init__(self, data_dir: str = None):
        """
        Initialise le constructeur de réseau.

        Args:
            data_dir: Chemin vers le répertoire des données, si None utilise le répertoire par défaut
        """
        self.data_loader = NetworkDataLoader(data_dir)
        self.current_network = None

    async def create_network(self, scenario,liste_infra, year: str = None, start_date=None, end_date=None) -> pypsa.Network:
        """
        Crée et configure le réseau à partir des données CSV et d'un scénario.

        Args:
            scenario: Objet scénario contenant les paramètres temporels (dates début/fin et pas de temps)
            year: Année des données (ex: '2024') pour les données statiques optionnelles

        Returns:
            network: Réseau PyPSA configuré

        Example:
            >>> scenario = read_scenario_by_id(db, 1)
            >>> network = builder.create_network(scenario, '2024')
        """
        # Chargement des données statiques
        self.data_loader.set_infrastructure_ids(liste_infra)
        network = await self.data_loader.load_network_data()
        
        # Ajout des séries temporelles
        network = await self.data_loader.load_timeseries_data(
            network=network, 
            scenario=scenario,
            year=year,
            start_date=start_date,
            end_date=end_date
        )
        
        self.current_network = network
        return network

    def optimize_network(self, 
                        network: Optional[pypsa.Network] = None,
                        solver_name: str = "highs") -> pypsa.Network:
        """
        Optimise la production sur le réseau.

        Args:
            network: Réseau à optimiser (utilise current_network si None)
            solver_name: Solveur à utiliser pour l'optimisation

        Returns:
            network: Réseau avec les résultats d'optimisation
        """
        if network is None:
            network = self.current_network
            
        if network is None:
            raise ValueError("Aucun réseau disponible pour l'optimisation")

        optimizer = NetworkOptimizer(network, solver_name)
        network = optimizer.optimize()
        
        self.current_network = network
        return network

    def run_power_flow(self,
                    network: Optional[pypsa.Network] = None,
                    mode: str = "dc") -> Tuple[pypsa.Network, Dict]:
        """
        Exécute un calcul de flux de puissance et analyse les résultats.

        Args:
            network: Réseau à analyser (utilise current_network si None)
            mode: Type de calcul ('ac' ou 'dc')

        Returns:
            Tuple[network, results]: Réseau et résultats d'analyse

        Raises:
            ValueError: Si aucun réseau n'est disponible
        """
        if network is None:
            network = self.current_network
            
        if network is None:
            raise ValueError("Aucun réseau disponible pour le calcul")

        # Création de l'analyseur
        analyzer = PowerFlowAnalyzer(network, mode=mode)
        
        # Calcul du load flow
        success = analyzer.run_power_flow()
        
        if not success:
            raise RuntimeError("Le calcul de flux de puissance a échoué")
        
        # Collecte des résultats
        results = {
            "line_loading": analyzer.get_line_loading(),
            "critical_lines": analyzer.get_critical_lines(),
            "losses": analyzer.analyze_network_losses()
        }
        
        # Ajoute les résultats de tension si en mode AC
        if mode == "ac":
            results["voltage_profile"] = analyzer.get_voltage_profile()
        
        # Stocke l'analyseur pour une utilisation dans analyze_results
        self.power_flow_analyzer = analyzer
        self.current_network = network
        return network, results

    def analyze_results(self, 
                    network: Optional[pypsa.Network] = None,mode: str = "dc") -> Dict:
        """
        Analyse complète des résultats de simulation.

        Args:
            network: Réseau à analyser (utilise current_network si None)

        Returns:
            Dict: Ensemble des résultats d'analyse

        Note:
            Cette méthode suppose qu'un calcul de flux a déjà été effectué
        """
        if network is None:
            network = self.current_network
            
        if network is None:
            raise ValueError("Aucun réseau disponible pour l'analyse")

        # Réutilise l'analyseur précédent s'il existe et qu'il a bien calculé le power flow
        if hasattr(self, "power_flow_analyzer") and \
           self.power_flow_analyzer.network == network and \
           self.power_flow_analyzer.results_available:
            analyzer = self.power_flow_analyzer
        else:
            raise ValueError("Aucun résultat de calcul disponible")
        
        results = {
            "technical_analysis": {
                "line_loading": analyzer.get_line_loading(),
                "critical_lines": analyzer.get_critical_lines(),
                "losses": analyzer.analyze_network_losses()
            },
            "energy_balance": {
                "total_generation": network.generators_t.p.sum().sum(),
                "total_load": network.loads_t.p.sum().sum(),
                "generation_by_type": network.generators_t.p.groupby(
                    network.generators.carrier, axis=1
                ).sum().sum()
            }
        }
        return results
    
    # Add new method here
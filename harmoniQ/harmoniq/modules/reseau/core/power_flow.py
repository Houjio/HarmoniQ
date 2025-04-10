"""
Module de calcul et d'analyse des flux de puissance.

Ce module gère les calculs de flux de puissance et l'analyse des résultats
pour le réseau électrique d'Hydro-Québec. Il permet d'effectuer des calculs
AC et DC et d'analyser les flux dans les lignes.

Example:
    >>> from network.core import PowerFlowAnalyzer
    >>> analyzer = PowerFlowAnalyzer(network)
    >>> success = analyzer.run_power_flow()
    >>> results = analyzer.get_line_statistics()

Notes:
    Les calculs utilisent les données de :
    - buses.csv pour les points de connexion
    - lines.csv pour les caractéristiques des lignes
    - line_types.csv pour les paramètres standards

Contributeurs : Yanis Aksas (yanis.aksas@polymtl.ca)
                Add Contributor here
"""

import pypsa
import pandas as pd
from typing import Dict, List, Optional, Tuple
import numpy as np


class PowerFlowAnalyzer:
    """
    Analyseur de flux de puissance pour le réseau électrique.
    
    Cette classe gère les calculs de flux de puissance et fournit
    des méthodes d'analyse pour évaluer l'état du réseau.

    Attributes:
        network (pypsa.Network): Réseau à analyser
        mode (str): Mode de calcul par défaut ('ac' ou 'dc')
        results_available (bool): Indique si des résultats sont disponibles
    """

    def __init__(self, network: pypsa.Network, mode: str = "dc"):
        """
        Initialise l'analyseur de flux de puissance.

        Args:
            network: Réseau PyPSA à analyser
            mode: Mode de calcul par défaut ('ac' ou 'dc')
        """
        self.network = network
        self.mode = mode
        self.results_available = False

    def run_power_flow(self, 
                      snapshot: Optional[str] = None,
                      mode: Optional[str] = None) -> bool:
        """
        Exécute un calcul de flux de puissance.

        Args:
            snapshot: Instant spécifique à calculer
            mode: Mode de calcul (utilise le mode par défaut si None)

        Returns:
            bool: True si le calcul a convergé

        Note:
            Stocke les résultats dans network.lines_t.p0, network.lines_t.loading, etc.
        """
        try:
            calc_mode = mode if mode else self.mode
            
            if calc_mode == "ac":
                self.network.lpf(snapshots=snapshot)
                success = self.network.pf(snapshots=snapshot,x_tol=1e-5)
            else:
                success = self.network.lpf(snapshots=snapshot)

            self.results_available = True if success is None else success
            return self.results_available

        except Exception as e:
            print(f"Erreur lors du calcul de flux de puissance : {str(e)}")
            self.results_available = False
            return False

    def get_line_loading(self) -> pd.DataFrame:
        """
        Calcule le chargement des lignes.

        Returns:
            DataFrame avec pour chaque ligne :
            - Chargement en pourcentage
            - Flux de puissance
            - Marge disponible
        """
        if not self.results_available or self.network.lines_t.p0.empty:
            raise RuntimeError("Aucun résultat de calcul disponible")

        # Calculer le chargement en utilisant p0 (flux de puissance) et s_nom (capacité)
        power_flow = self.network.lines_t.p0
        capacity = self.network.lines.s_nom

        # Calculer le pourcentage de chargement manuellement
        loading_percent = (power_flow.abs() / capacity) * 100

        results = pd.DataFrame({
            'loading_percent': loading_percent.max(),
            'power_flow_mw': power_flow.abs().max(),
            'remaining_capacity_mw': capacity - power_flow.abs().max()
        })

        return results

    def get_critical_lines(self, threshold: float = 90.0) -> Dict[str, Dict]:
        """
        Identifie les lignes fortement chargées.

        Args:
            threshold: Seuil de chargement en pourcentage

        Returns:
            Dict des lignes critiques avec leurs caractéristiques
        """
        line_loading = self.get_line_loading()
        critical_lines = {}

        for line in line_loading[line_loading.loading_percent > threshold].index:
            critical_lines[line] = {
                'loading': line_loading.loc[line, 'loading_percent'],
                'power_flow': line_loading.loc[line, 'power_flow_mw'],
                'from_bus': self.network.lines.loc[line, 'bus0'],
                'to_bus': self.network.lines.loc[line, 'bus1']
            }

        return critical_lines

    def analyze_network_losses(self) -> Dict[str, float]:
        """
        Calcule les pertes dans le réseau.

        Returns:
            Dict contenant :
            - Pertes totales
            - Pourcentage des pertes
            - Pertes par niveau de tension
        """
        if not self.results_available:
            raise RuntimeError("Aucun résultat de calcul disponible")

        total_generation = self.network.generators_t.p.sum().sum()
        total_load = self.network.loads_t.p.sum().sum()
        losses = self.network.lines_t.p0.sum() + self.network.lines_t.p1.sum()

        return {
            'total_losses_mw': float(losses.sum()),
            'losses_percent': float(losses.sum() / total_generation * 100),
            'losses_by_voltage': self.network.lines.groupby('type',group_keys=False).apply(
                lambda x: (
                    self.network.lines_t.p0[x.index].sum() - 
                    self.network.lines_t.p1[x.index].sum()
                ).sum()
            ).to_dict()
        }

    def get_voltage_profile(self) -> Optional[pd.DataFrame]:
        """
        Analyse les profils de tension (mode AC uniquement).

        Returns:
            DataFrame avec les tensions aux bus ou None en mode DC
        """
        if not self.results_available:
            raise RuntimeError("Aucun résultat de calcul disponible")

        if self.mode == "dc":
            return None

        return pd.DataFrame({
            'voltage_pu': self.network.buses_t.v_mag_pu.mean(),
            'voltage_min': self.network.buses_t.v_mag_pu.min(),
            'voltage_max': self.network.buses_t.v_mag_pu.max(),
            'angle_deg': self.network.buses_t.v_ang.mean() * 180 / np.pi
        })
    
    # Add new method here
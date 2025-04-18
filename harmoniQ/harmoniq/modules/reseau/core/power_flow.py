"""
Module de calcul et d'analyse des flux de puissance.

Gère les calculs de flux de puissance (AC et DC) et l'analyse des résultats
pour le réseau électrique.

Contributeurs : Yanis Aksas (yanis.aksas@polymtl.ca)
"""

import pypsa
import pandas as pd
from typing import Dict, List, Optional, Tuple
import numpy as np


class PowerFlowAnalyzer:
    """
    Analyseur de flux de puissance pour le réseau électrique.
    
    Gère les calculs de flux de puissance et fournit des méthodes d'analyse
    pour évaluer l'état du réseau.

    Attributes:
        network: Réseau à analyser
        mode: Mode de calcul par défaut ('ac' ou 'dc')
        results_available: Indique si des résultats sont disponibles
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
            
            if (calc_mode == "ac"):
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

    
    # Add new method here
"""
Module d'optimisation du réseau électrique.

Ce module gère l'optimisation de la production électrique en utilisant PyPSA.
L'optimisation est basée sur :
- Les coûts marginaux des centrales pilotables (réservoirs, thermique)
- La disponibilité des centrales non-pilotables (fil de l'eau, éolien, solaire)
- Les contraintes du réseau de transport

Example:
    >>> from network.core import NetworkOptimizer
    >>> optimizer = NetworkOptimizer(network)
    >>> network = optimizer.optimize()
    >>> results = optimizer.get_optimization_results()

Notes:
    L'optimisation utilise :
    - generators-p_max_pu.csv pour les contraintes des non-pilotables
    - generators-marginal_cost.csv pour le pilotage des réservoirs
    - Les contraintes de réseau définies dans lines.csv

Contributeurs : Yanis Aksas (yanis.aksas@polymtl.ca)
                Add Contributor here
"""

import pypsa
import pandas as pd
from typing import Dict, Optional, Tuple
from datetime import datetime


class NetworkOptimizer:
    """
    Optimiseur du réseau électrique.
    
    Cette classe gère l'optimisation de la production en minimisant les coûts
    tout en respectant les contraintes du réseau. Elle utilise les coûts marginaux
    pour piloter les centrales à réservoir.

    Attributes:
        network (pypsa.Network): Réseau à optimiser
        solver_name (str): Solveur à utiliser
        solver_options (dict): Options de configuration du solveur
    """

    def __init__(self, network: pypsa.Network, solver_name: str = "highs"):
        """
        Initialise l'optimiseur.

        Args:
            network: Réseau PyPSA à optimiser
            solver_name: Nom du solveur linéaire à utiliser ('highs' par défaut)
        """
        self.network = network
        self.solver_name = solver_name

    def optimize(self) -> pypsa.Network:
        """
        Exécute l'optimisation du réseau.

        Cette méthode optimise la production en minimisant les coûts totaux,
        en respectant :
        - La disponibilité des sources non-pilotables (p_max_pu)
        - Les coûts marginaux des sources pilotables
        - Les contraintes de transport

        Returns:
            Le réseau avec les résultats d'optimisation

        Raises:
            RuntimeError: Si l'optimisation échoue
        """
        try:
            # Configuration de l'optimisation
            self.network.optimize.load_shedding = False
            self.network.optimize.noisy_costs = True
            
            # Lance l'optimisation
            status, termination_condition = self.network.optimize(solver_name=self.solver_name)
            
            if status != "ok":
                raise RuntimeError(f"Optimisation échouée avec statut: {status}")
            
            return self.network
            
        except Exception as e:
            raise RuntimeError(f"Erreur lors de l'optimisation: {str(e)}")

    def get_optimization_results(self) -> Dict:
        """
        Récupère les résultats détaillés de l'optimisation.

        Returns:
            Dict contenant :
            - Production par type de centrale
            - Coûts totaux
            - Statistiques d'utilisation des réservoirs
            - Contraintes actives
        """
        if not hasattr(self.network, 'objective'):
            raise RuntimeError("Aucun résultat d'optimisation disponible")

        # Sépare les générateurs par type
        pilotable_gens = self.network.generators[
            self.network.generators.carrier.isin(['hydro_reservoir', 'thermique'])
        ].index
        non_pilotable_gens = self.network.generators[
            self.network.generators.carrier.isin(['hydro_fil', 'eolien', 'solaire'])
        ].index

        results = {
            # Résultats globaux
            "status": getattr(self.network, 'status', 'unknown'),
            "objective_value": float(self.network.objective),
            "total_cost": float(self.network.objective),
            
            # Production par type
            "pilotable_production": self.network.generators_t.p[pilotable_gens].sum(),
            "non_pilotable_production": self.network.generators_t.p[non_pilotable_gens].sum(),
            
            # Statistiques par carrier
            "production_by_type": self.network.generators_t.p.groupby(
                self.network.generators.carrier, axis=1
            ).sum(),
            
            # Contraintes actives
            "line_loading_max": self.network.lines_t.p0.abs().max(),
            "n_active_line_constraints": (
                self.network.lines_t.p0.abs() > 0.99 * self.network.lines.s_nom
            ).sum().sum(),
            "global_constraints": self.network.global_constraints if hasattr(self.network, "global_constraints") else None
            
        }
        
        return results

    def check_optimization_feasibility(self) -> Tuple[bool, str]:
        """
        Vérifie si l'optimisation est faisable.

        Returns:
            Tuple[faisable, message]: Statut de faisabilité et message explicatif
        """
        try:
            # Vérifie la capacité totale
            total_capacity = self.network.generators.p_nom.sum()
            max_load = self.network.loads_t.p_set.sum(axis=1).max()
            
            if total_capacity < max_load:
                return False, f"Capacité insuffisante: {total_capacity:.0f} MW < {max_load:.0f} MW"
                       
            return True, "Optimisation faisable"
            
        except Exception as e:
            return False, f"Erreur lors de la vérification: {str(e)}"
    
    # Add new method here
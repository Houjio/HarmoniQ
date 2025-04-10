"""
Module de visualisation du réseau électrique.

Ce module fournit des outils de visualisation pour analyser le réseau
électrique d'Hydro-Québec, incluant :
- Carte du réseau (buses, lignes, centrales)
- Visualisation des charges
- Analyse temporelle de la production
- Statistiques de flux de puissance
- ++

Example:
    >>> from network.utils import NetworkVisualizer
    >>> visualizer = NetworkVisualizer(network)
    >>> visualizer.plot_network_map()
    >>> visualizer.plot_load_distribution()

Notes:
    Les couleurs utilisées pour les visualisations sont définies dans
    carriers.csv pour assurer une cohérence visuelle.

Contributeurs : Yanis Aksas (yanis.aksas@polymtl.ca)
                Add Contributor here
"""

import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Optional, List, Tuple


class NetworkVisualizer:
    """
    Visualiseur du réseau électrique.
    
    Cette classe fournit des méthodes pour créer différentes
    visualisations du réseau et de son fonctionnement.

    Attributes:
        network (pypsa.Network): Réseau à visualiser
        colors (Dict): Couleurs par type de production
    """

    def __init__(self, network: pypsa.Network):
        """
        Initialise le visualiseur.

        Args:
            network: Réseau PyPSA à visualiser
        """
        self.network = network
        self.colors = dict(zip(
            self.network.carriers.index,
            self.network.carriers.color
        ))

    def plot_network_map(self, 
                        interactive: bool = True,
                        save_path: Optional[str] = None) -> None:
        """
        Crée une carte du réseau en utilisant les fonctions natives de PyPSA.

        Args:
            interactive: Si True, utilise network.iplot(), sinon network.plot()
            save_path: Chemin pour sauvegarder la visualisation
        """
        if interactive:
            # Utilise plotly (interactif)
            self.network.iplot(
                bus_colors='cadetblue',
                line_colors='rosybrown',
                link_colors='darkseagreen',
                bus_sizes=10,
                line_widths=3,
                title='Réseau Hydro-Québec'
            )
        else:
            # Utilise matplotlib (statique)
            self.network.plot(
                bus_colors='cadetblue',
                line_colors='rosybrown',
                bus_sizes=0.02,
                line_widths=1.5,
                title='Réseau Hydro-Québec'
            )
            
        if save_path:
            plt.savefig(save_path)
            
        #Voir comment faire une vraie carte du réseau

    def plot_load_profile(self, 
                         period: Optional[str] = None,
                         aggregated: bool = True) -> None:
        """
        Visualise les profils de charge.

        Args:
            period: Période spécifique à visualiser
            aggregated: Si True, agrège toutes les charges
        """
        plt.figure(figsize=(12, 6))
        
        if aggregated:
            total_load = self.network.loads_t.p_set.sum(axis=1)
            plt.plot(total_load.index, total_load.values, 'b-', label='Charge totale')
        else:
            for load in self.network.loads_t.p_set.columns:
                plt.plot(
                    self.network.loads_t.p_set.index,
                    self.network.loads_t.p_set[load],
                    label=load
                )

        plt.title('Profil de charge')
        plt.xlabel('Temps')
        plt.ylabel('Puissance (MW)')
        plt.grid(True)
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()

    def plot_marginal_costs(self) -> None:
        """
        Visualise l'évolution des coûts marginaux des centrales pilotables.
        """
        plt.figure(figsize=(12, 6))
        
        for gen in self.network.generators[
            self.network.generators.carrier == 'hydro_reservoir'
        ].index:
            plt.plot(
                self.network.generators_t.marginal_cost.index,
                self.network.generators_t.marginal_cost[gen],
                label=gen
            )

        plt.title('Évolution des coûts marginaux')
        plt.xlabel('Temps')
        plt.ylabel('Coût marginal')
        plt.grid(True)
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()

    def create_network_report(self, 
                            output_dir: str,
                            timestamp: Optional[str] = None) -> None:
        """
        Génère un rapport complet avec toutes les visualisations.

        Args:
            output_dir: Répertoire de sortie
            timestamp: Instant spécifique pour certaines visualisations
        """
        # Carte du réseau
        self.plot_network_map(save_path=f"{output_dir}/network_map.html")
        
        # Profils de charge
        self.plot_load_profile()
        plt.savefig(f"{output_dir}/load_profile.png")
        
        # Coûts marginaux
        self.plot_marginal_costs()
        plt.savefig(f"{output_dir}/marginal_costs.png")

    # Add new method here


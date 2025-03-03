"""
Module d'utilitaires géographiques pour le réseau électrique.

Ce module fournit des fonctions pour les calculs géographiques liés au réseau
électrique d'Hydro-Québec, notamment le calcul des distances entre les composants
du réseau et l'optimisation des tracés des lignes de transmission.

Classes:
    GeoUtils: Classe principale pour les calculs géographiques.

Functions:
    calculate_distance: Calcule la distance entre deux points.
    optimize_line_path: Optimise le tracé d'une ligne entre deux points.

Example:
    >>> from network.utils import GeoUtils
    >>> geo = GeoUtils()
    >>> distance = geo.calculate_distance(
    ...     (45.5017, -73.5673),  # Montréal
    ...     (46.8139, -71.2080)   # Québec
    ... )
    >>> print(f"Distance: {distance:.2f} km")

Notes:
    Toutes les coordonnées sont attendues au format (latitude, longitude)
    en degrés décimaux.

Contributeurs : Yanis Aksas (yanis.aksas@polymtl.ca)
                Add Contributor here
"""

import numpy as np
import math
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from math import radians, sin, cos, sqrt, atan2


@dataclass
class Point:
    """
    Représentation d'un point géographique.

    Attributes:
        lat (float): Latitude en degrés décimaux
        lon (float): Longitude en degrés décimaux
        name (str, optional): Nom du point pour identification
    """
    lat: float
    lon: float
    name: Optional[str] = None


class GeoUtils:
    """
    Classe utilitaire pour les calculs géographiques du réseau.
    
    Cette classe fournit des méthodes pour calculer les distances
    entre les composants du réseau et optimiser les tracés des lignes
    de transmission en tenant compte des contraintes géographiques.
    
    Note:
        Tous les calculs de distance utilisent la formule de Haversine (Length_calculator.py).
    """

    EARTH_RADIUS = 6371.0  # Rayon moyen de la Terre en km

    def calculate_distance(self,
                         point1: Tuple[float, float],
                         point2: Tuple[float, float]) -> float:
        """
        Calcule la distance entre deux points en kilomètres.

        Args:
            point1: Tuple (latitude, longitude) du premier point
            point2: Tuple (latitude, longitude) du deuxième point

        Returns:
            Distance en kilomètres

        Example:
            >>> geo = GeoUtils()
            >>> mtl = (45.5017, -73.5673)
            >>> qc = (46.8139, -71.2080)
            >>> dist = geo.calculate_distance(mtl, qc)
        """
        lat1, lon1 = map(radians, point1)
        lat2, lon2 = map(radians, point2)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        return self.EARTH_RADIUS * c


    def calculate_line_length(self, 
                            points: List[Tuple[float, float]]) -> float:
        """
        Calcule la longueur totale d'une ligne passant par plusieurs points.

        Cette méthode est utilisée pour calculer la longueur réelle des
        lignes de transmission qui peuvent avoir des points intermédiaires.

        Args:
            points: Liste de tuples (latitude, longitude)

        Returns:
            Longueur totale en kilomètres

        Example:
            >>> line_points = [(45.5, -73.5), (46.0, -72.8), (46.8, -71.2)]
            >>> length = geo.calculate_line_length(line_points)
        """
        total_length = 0.0
        for i in range(len(points) - 1):
            total_length += self.calculate_distance(points[i], points[i + 1])
        return total_length
    
    # Add new method here
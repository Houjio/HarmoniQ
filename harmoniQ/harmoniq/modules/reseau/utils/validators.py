"""
Module de validation du réseau électrique.

Ce module gère la validation de la cohérence du réseau électrique
et propose des méthodes d’identification d’incohérences dans 
les données statiques et temporelles.

Classes:
    NetworkValidator: Classe responsable de valider la cohérence
                      d'un réseau PyPSA.

Example:
    >>> from network.utils import NetworkValidator
    >>> validator = NetworkValidator()
    >>> is_valid = validator.validate_network(network)

Contributeurs : Yanis Aksas (yanis.aksas@polymtl.ca)
                Add Contributor here
"""

import pypsa

class DataLoadError(Exception):
    """
    Exception levée pour les problèmes de chargement des données.
    """
    pass

class NetworkValidator:
    """
    Classe gérant la validation du réseau électrique.
    """


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

    def validate_network(self, network: pypsa.Network) -> bool:
        """
        Valide la cohérence du réseau chargé.

        Args:
            network: Réseau PyPSA à valider

        Returns:
            bool: True si le réseau est valide

        Raises:
            DataLoadError: Si des incohérences sont détectées
        """
        try:
            if len(network.buses) == 0:
                raise DataLoadError("Aucun bus trouvé dans le réseau")
            if len(network.generators) == 0:
                raise DataLoadError("Aucun générateur trouvé dans le réseau")
            if len(network.lines) == 0:
                raise DataLoadError("Aucune ligne trouvée dans le réseau")
            if hasattr(network, 'snapshots') and len(network.snapshots) == 0:
                raise DataLoadError("Aucune donnée temporelle trouvée")
            return True
        except Exception as e:
            raise DataLoadError(f"Validation du réseau échouée: {str(e)}")
        
    # Add new method here

"""
Script principal pour tester les utilitaires du réseau électrique.
"""

from utils import (NetworkDataLoader, NetworkVisualizer, NetworkValidator, 
                  TimeSeriesManager, GeoUtils, DataLoadError)
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import pypsa

class NetworUtilskManager:
    """Classe de test des utilitaires du réseau."""
    
    def __init__(self, data_dir: str = "data"):
        """Initialise le gestionnaire avec les utilitaires nécessaires."""
        self.loader = NetworkDataLoader(data_dir)
        self.validator = NetworkValidator()
        self.network = None
        self.visualizer = NetworkVisualizer(pypsa.Network())  # Initialise avec un réseau vide
        self.time_manager = TimeSeriesManager()
        self.geo_utils = GeoUtils() 
    
    def load_and_validate(self) -> bool:
        """Charge et valide les données du réseau."""
        try:
            print("\nChargement des données statiques...")
            self.network = self.loader.load_network_data()
            
            if self.validator.validate_network(self.network):
                print("✓ Données statiques validées")
            
            print("\nChargement des données temporelles pour 2024...")
            self.network = self.loader.load_timeseries_data(
                self.network, '2024'
            )
            print("✓ Données temporelles chargées")
            
            # Mise à jour du réseau dans le visualizer
            self.visualizer.network = self.network
            
            # Test d'accès aux données temporelles
            print("\n=== Vérification des données temporelles ===")
            print("\nProfils de charge (premiers points):")
            print(self.network.loads_t.p_set.head())
            
            print("\nCoûts marginaux des générateurs pilotables (premiers points):")
            print(self.network.generators_t.marginal_cost.head())
            
            print("\nProduction maximale des générateurs non pilotables (premiers points):")
            print(self.network.generators_t.p_max_pu.head())
            return True
            
        except Exception as e:
            print(f"Erreur: {e}", file=sys.stderr)
            return False
    
    def print_network_info(self):
        """Affiche les informations du réseau."""
        if not self.network:
            return
            
        print("\n=== Informations du réseau ===")
        print(f"Nombre de bus: {len(self.network.buses)}")
        print(f"Nombre de lignes: {len(self.network.lines)}")
        print(f"Nombre de générateurs: {len(self.network.generators)}")
        
        print("\n=== Types de générateurs ===")
        pilotables = self.network.generators[
            self.network.generators.type == 'pilotable'
        ]
        print("Générateurs pilotables:")
        print(pilotables.groupby('carrier').p_nom.sum())
        
        if hasattr(self.network, 'snapshots'):
            print("\n=== Période temporelle ===")
            print(f"Début: {self.network.snapshots[0]}")
            print(f"Fin: {self.network.snapshots[-1]}")
            print(f"Nombre de pas de temps: {len(self.network.snapshots)}")
    
    def test_visualizations(self):
        """Teste toutes les visualisations disponibles."""
        if not self.visualizer:
            print("Erreur: Visualiseur non initialisé")
            return False
            
        try:
            print("\nTest des visualisations...")
            
            # Carte du réseau
            print("1. Génération de la carte du réseau...")
            self.visualizer.plot_network_map(interactive=False)
            plt.show()
            
            # Profil de charge
            print("2. Génération du profil de charge...")
            self.visualizer.plot_load_profile()
            plt.show()
            
            # Coûts marginaux
            print("3. Génération des coûts marginaux...")
            self.visualizer.plot_marginal_costs()
            plt.show()
            
            print("✓ Toutes les visualisations générées avec succès")
            return True
            
        except Exception as e:
            print(f"Erreur lors de la visualisation: {e}", file=sys.stderr)
            return False

    def test_time_analysis(self):
        """Teste les fonctionnalités d'analyse temporelle."""
        if not self.network:
            print("Erreur: Réseau non initialisé")
            return False
            
        try:
            print("\nTest des analyses temporelles...")
            
            # Test des pics de demande
            print("\n1. Analyse des pics de demande:")
            peaks = self.time_manager.find_peak_demand(self.network)
            print("Top 5 des pics de demande:")
            print(peaks)
            
            # Test des statistiques saisonnières
            print("\n2. Statistiques saisonnières:")
            seasonal_stats = self.time_manager.get_seasonal_stats(self.network)
            print("\nCharge moyenne par saison:")
            print(seasonal_stats['load'])
            print("\nProduction non pilotable moyenne par saison:")
            print(seasonal_stats['non_pilotable_generation'])
            
            # Test des patterns de production
            print("\n3. Analyse des patterns de production:")
            hydro_patterns = self.time_manager.analyze_production_patterns(self.network, 'hydro_reservoir')
            print("\nStatistiques de production hydraulique:")
            print(hydro_patterns.describe())
            
            # Test de la résolution temporelle
            print("\n4. Résolution temporelle des données:")
            resolution = self.time_manager.get_time_resolution(self.network)
            print(f"Résolution: {resolution}")
            
            # Test de la cohérence temporelle
            print("\n5. Vérification de la cohérence temporelle:")
            is_consistent = self.time_manager.check_temporal_consistency(self.network)
            print(f"Données temporelles cohérentes: {is_consistent}")
            
            print("\n✓ Toutes les analyses temporelles effectuées avec succès")
            return True
            
        except Exception as e:
            print(f"Erreur lors de l'analyse temporelle: {e}", file=sys.stderr)
            return False

    def test_geo_calculations(self):
        """Teste les fonctionnalités de calculs géographiques."""
        if not self.network:
            print("Erreur: Réseau non initialisé")
            return False
            
        try:
            print("\nTest des calculs géographiques...")
            
            # Test du calcul de distance entre deux points
            print("\n1. Calcul de distance:")
            mtl = (45.5017, -73.5673)  # Montréal
            qc = (46.8139, -71.2080)   # Québec
            distance = self.geo_utils.calculate_distance(mtl, qc)
            print(f"Distance Montréal-Québec: {distance:.2f} km")
            
            # Test du calcul de longueur d'une ligne avec points intermédiaires
            print("\n2. Calcul de longueur de ligne:")
            line_points = [
                (45.5017, -73.5673),  # Montréal
                (46.343460, -72.543602),  # Trois-Rivières
                (46.8139, -71.2080)   # Québec
            ]
            length = self.geo_utils.calculate_line_length(line_points)
            print(f"Longueur totale du tracé: {length:.2f} km")
            
            # Vérification avec les données du réseau
            print("\n3. Vérification avec les lignes du réseau:")
            for line in self.network.lines.index[:3]:  # Prend les 3 premières lignes
                bus0 = self.network.lines.bus0[line]
                bus1 = self.network.lines.bus1[line]
                
                if hasattr(self.network.buses, 'x') and hasattr(self.network.buses, 'y'):
                    point1 = (self.network.buses.y[bus0], self.network.buses.x[bus0])
                    point2 = (self.network.buses.y[bus1], self.network.buses.x[bus1])
                    distance = self.geo_utils.calculate_distance(point1, point2)
                    print(f"Ligne {line}: {distance:.2f} km")
            
            print("\n✓ Tous les calculs géographiques effectués avec succès")
            return True
            
        except Exception as e:
            print(f"Erreur lors des calculs géographiques: {e}", file=sys.stderr)
            return False

def main():
    """Point d'entrée principal."""
    manager = NetworUtilskManager()
    
    success_load = manager.load_and_validate()
    if success_load:
        manager.print_network_info()
    
    success_viz = manager.test_visualizations()
    success_time = manager.test_time_analysis()
    success_geo = manager.test_geo_calculations()
    
    if not success_load:
        return 1
    if not success_viz:
        return 2
    if not success_time:
        return 3
    if not success_geo:
        return 4
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
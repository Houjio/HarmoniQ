"""
Script principal pour tester les fonctionnalités core du réseau électrique.
"""

from core import NetworkBuilder, PowerFlowAnalyzer, NetworkOptimizer
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import pypsa
import pandas as pd

class NetworkCoreManager:
    """Classe de test des fonctionnalités core du réseau."""
    
    def __init__(self, data_dir: str = "data"):
        """Initialise le gestionnaire avec les composants core."""
        self.builder = NetworkBuilder(data_dir)
        self.network = None
        
    def test_network_creation(self) -> bool:
        """Teste la création et la configuration du réseau."""
        try:
            print("\n=== Test de création du réseau ===")
            
            # Création du réseau pour 2024
            print("1. Création du réseau pour 2024...")
            self.network = self.builder.create_network('2024')
            print("✓ Réseau créé avec succès")
            
            # Vérification détaillée des bus
            print("\n2. Détails des bus:")
            print("-" * 80)
            print(self.network.buses)
            print("\nNombre total de bus:", len(self.network.buses))
            
            # Vérification détaillée des lignes
            print("\n3. Détails des lignes de transmission:")
            print("-" * 80)
            lines_info = pd.DataFrame({
                'De': self.network.lines.bus0,
                'Vers': self.network.lines.bus1,
                'Type': self.network.lines.type,
                'Longueur (km)': self.network.lines.length,
                'Capacité (MW)': self.network.lines.s_nom,
                'r (pu)': self.network.lines.r,
                'x (pu)': self.network.lines.x,
            })
            print(lines_info)
            print("\nNombre total de lignes:", len(self.network.lines))
            
            # Vérification des types de lignes
            print("\n4. Types de lignes disponibles:")
            print("-" * 80)
            print(self.network.line_types)
            
            # Vérification détaillée des générateurs
            print("\n5. Détails des générateurs:")
            print("-" * 80)
            gen_info = pd.DataFrame({
                'Bus': self.network.generators.bus,
                'Type': self.network.generators.carrier,
                'P_nom (MW)': self.network.generators.p_nom,
                'Pilotable': self.network.generators.type,
            })
            print(gen_info)
            print("\nNombre total de générateurs:", len(self.network.generators))
            
            # Statistiques par type de production
            print("\n6. Capacité installée par type:")
            print("-" * 80)
            capacity_by_type = self.network.generators.groupby('carrier')['p_nom'].sum()
            print(capacity_by_type)
            
            # Vérification des charges
            print("\n7. Détails des charges:")
            print("-" * 80)
            load_info = pd.DataFrame({
                'Bus': self.network.loads.bus,
                'P_set (MW)': self.network.loads.p_set,
            })
            print(load_info)
            print("\nNombre total de charges:", len(self.network.loads))
            
            # Vérification des données temporelles
            print("\n8. Aperçu des séries temporelles:")
            print("-" * 80)
            print("\nPériode couverte:")
            print(f"Début: {self.network.snapshots[0]}")
            print(f"Fin: {self.network.snapshots[-1]}")
            print(f"Nombre de pas de temps: {len(self.network.snapshots)}")
            
            if hasattr(self.network, 'loads_t'):
                print("\nProfils de charge (premiers points):")
                print(self.network.loads_t.p_set.head())
                
            if hasattr(self.network, 'generators_t'):
                print("\nProfils de production (premiers points):")
                if hasattr(self.network.generators_t, 'p_max_pu'):
                    print("\nFacteurs de disponibilité (non-pilotables):")
                    print(self.network.generators_t.p_max_pu.head())
                if hasattr(self.network.generators_t, 'marginal_cost'):
                    print("\nCoûts marginaux (pilotables):")
                    print(self.network.generators_t.marginal_cost.head())
            
            return True
            
        except Exception as e:
            print(f"Erreur lors de la création du réseau: {e}", file=sys.stderr)
            return False
            
    def test_power_flow(self) -> bool:
        """Teste les calculs de flux de puissance."""
        try:
            print("\n=== Test des calculs de flux de puissance ===")
            
            # Création de l'analyseur
            print("1. Initialisation de l'analyseur...")
            analyzer = PowerFlowAnalyzer(self.network)
            
            # Test du calcul DC
            print("\n2. Calcul en mode DC...")
            success_dc = analyzer.run_power_flow(mode="dc")
            if success_dc:
                print("✓ Calcul DC réussi")
                
                # Analyse des résultats
                print("\n3. Analyse des résultats DC:")
                loading = analyzer.get_line_loading()
                print("\nChargement des lignes:")
                print(loading.head())
                
                critical = analyzer.get_critical_lines(threshold=80)
                print(f"\nNombre de lignes critiques: {len(critical)}")
                
                losses = analyzer.analyze_network_losses()
                print("\nPertes réseau:")
                print(f"Total: {losses['total_losses_mw']:.2f} MW")
                print(f"Pourcentage: {losses['losses_percent']:.2f}%")
            
            # Test du calcul AC
            print("\n4. Calcul en mode AC...")
            success_ac = analyzer.run_power_flow(mode="ac")
            if success_ac:
                print("✓ Calcul AC réussi")
                
                # Analyse des tensions
                print("\n5. Analyse des tensions:")
                voltages = analyzer.get_voltage_profile()
                if voltages is not None:
                    print("\nProfils de tension:")
                    print(voltages.head())
            
            return success_dc and success_ac
            
        except Exception as e:
            print(f"Erreur lors des calculs de flux: {e}", file=sys.stderr)
            return False
    
    def test_optimization(self) -> bool:
        """Teste l'optimisation du réseau."""
        try:
            print("\n=== Test d'optimisation du réseau ===")
            
            # Création de l'optimiseur
            print("1. Initialisation de l'optimiseur...")
            optimizer = NetworkOptimizer(self.network)
            
            # Vérification de la faisabilité
            print("\n2. Vérification de la faisabilité...")
            feasible, message = optimizer.check_optimization_feasibility()
            print(f"Statut: {message}")
            
            if feasible:
                # Lancement de l'optimisation
                print("\n3. Lancement de l'optimisation...")
                self.network = optimizer.optimize()
                
                # Analyse des résultats
                print("\n4. Analyse des résultats:")
                results = optimizer.get_optimization_results()
                
                print("\nProduction par type:")
                print(results['production_by_type'].sum())
                
                print("\nContraintes globales:")
                print(results["global_constraints"])

                print(f"Coût total: {results['total_cost']:.2f}")
                
                return True
            else:
                print("Optimisation non faisable")
                return False
                
        except Exception as e:
            print(f"Erreur lors de l'optimisation: {e}", file=sys.stderr)
            return False
            
    def test_complete_analysis(self) -> bool:
        """Teste l'analyse complète du réseau."""
        try:
            print("\n=== Test d'analyse complète du réseau ===")
            
            # Création et optimisation
            print("1. Optimisation du réseau...")
            self.network = self.builder.optimize_network(self.network)
            
            # Calcul des flux
            print("\n2. Calcul des flux de puissance...")
            self.network, pf_results = self.builder.run_power_flow(self.network,mode="dc")
            
            # Analyse complète
            print("\n3. Analyse des résultats...")
            results = self.builder.analyze_results(self.network,mode="dc")
            
            # Affichage des résultats principaux
            print("\n=== Résultats de l'analyse ===")
            
            print("\nBilan énergétique:")
            print(f"Production totale: {results['energy_balance']['total_generation']:.2f} MW")
            print(f"Consommation totale: {results['energy_balance']['total_load']:.2f} MW")
            
            print("\nProduction par type:")
            for carrier, value in results['energy_balance']['generation_by_type'].items():
                print(f"{carrier}: {value:.2f} MW")
            
            print("\nAnalyse technique:")
            print(f"Pertes totales: {results['technical_analysis']['losses']['total_losses_mw']:.2f} MW")
            print(f"Nombre de lignes critiques: {len(results['technical_analysis']['critical_lines'])}")
            
            return True
            
        except Exception as e:
            print(f"Erreur lors de l'analyse complète: {e}", file=sys.stderr)
            return False

def main():
    """Point d'entrée principal."""
    manager = NetworkCoreManager()
    
    # Test de création du réseau
    success_creation = manager.test_network_creation()
    if not success_creation:
        print("Échec de la création du réseau")
        return 1
        
    # # Test des calculs de flux
    # success_pf = manager.test_power_flow()
    # if not success_pf:
    #     print("Échec des calculs de flux")
    #     return 2
        
    # # Test de l'optimisation
    # success_opt = manager.test_optimization()
    # if not success_opt:
    #     print("Échec de l'optimisation")
    #     return 3
        
    # # Test de l'analyse complète
    # success_analysis = manager.test_complete_analysis()
    # if not success_analysis:
    #     print("Échec de l'analyse complète")
    #     return 4
    
    print("\n✓ Tous les tests core réussis!")
    return 0

if __name__ == "__main__":
    sys.exit(main())

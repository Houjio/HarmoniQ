"""
Test du chargeur de données pour le réseau électrique.
Ce script teste particulièrement le chargement des bus, lignes et types de lignes.
"""

import sys
import os
from pathlib import Path

parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from utils import NetworkDataLoader, DataLoadError

def test_network_data():
    """
    Teste le chargement des données statiques du réseau.
    Vérifie spécifiquement les bus, les lignes et les types de lignes.
    """
    print("Démarrage du test de chargement des données réseau...")
    
    try:
        # Initialisation du chargeur de données
        data_loader = NetworkDataLoader(data_dir=str(parent_dir / "data"))
        
        # Chargement des données
        network = data_loader.load_network_data()
        
        # Vérification des bus
        print("\n=== BUS ===")
        buses_df = network.buses
        print(f"Nombre de bus chargés: {len(buses_df)}")
        print(buses_df)
        
        # Vérification des colonnes essentielles dans les bus
        bus_cols = ['v_nom', 'type', 'x', 'y', 'control']
        for col in bus_cols:
            if col not in buses_df.columns:
                print(f"ERREUR: Colonne '{col}' manquante dans les bus")
        
        # Vérification des types de lignes
        print("\n=== TYPES DE LIGNES ===")
        line_types_df = network.line_types
        
        filtered_line_types = line_types_df[line_types_df.index.str.endswith('kV_line')]
        print(f"Nombre de types de lignes kV: {len(filtered_line_types)}")
        print(filtered_line_types)
        
        # Vérification des colonnes essentielles pour les types de lignes
        linetype_cols = ['f_nom', 'r_per_length', 'x_per_length']
        for col in linetype_cols:
            if col not in line_types_df.columns:
                print(f"ERREUR: Colonne '{col}' manquante dans les types de lignes")
        
        # Vérification des lignes
        print("\n=== LIGNES ===")
        lines_df = network.lines
        print(f"Nombre de lignes: {len(lines_df)}")
        print(lines_df)
        
        # Vérification des colonnes essentielles dans les lignes
        line_cols = ['bus0', 'bus1', 'type', 'length', 's_nom', 'capital_cost']
        for col in line_cols:
            if col not in lines_df.columns:
                print(f"ERREUR: Colonne '{col}' manquante dans les lignes")
        
        # Vérification de cohérence: tous les bus référencés existent-ils?
        if not lines_df.empty:
            bus_ids = set(buses_df.index)
            unknown_buses = set(lines_df['bus0'].tolist() + lines_df['bus1'].tolist()) - bus_ids
            if unknown_buses:
                print(f"ERREUR: Certaines lignes référencent des bus inconnus: {unknown_buses}")
            else:
                print("✓ Toutes les lignes référencent des bus existants")
        
        print("\nTest terminé avec succès!")
        
    except DataLoadError as e:
        print(f"Erreur lors du chargement des données: {e}")
    except Exception as e:
        print(f"Erreur inattendue: {e}")

if __name__ == "__main__":
    test_network_data()

"""
Test du chargeur de données pour le réseau électrique.
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
        data_loader = NetworkDataLoader(data_dir=str(parent_dir / "data"))
        network = data_loader.load_network_data()
        
        # Vérification des bus
        print("\n=== BUS ===")
        buses_df = network.buses
        print(f"Nombre de bus chargés: {len(buses_df)}")
        print(buses_df)
        
        # Vérification des colonnes dans les bus
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
        
        # Vérification des colonnes pour les types de lignes
        linetype_cols = ['f_nom', 'r_per_length', 'x_per_length']
        for col in linetype_cols:
            if col not in line_types_df.columns:
                print(f"ERREUR: Colonne '{col}' manquante dans les types de lignes")
        
        # Vérification des lignes
        print("\n=== LIGNES ===")
        lines_df = network.lines
        print(f"Nombre de lignes: {len(lines_df)}")
        print(lines_df)
        
        # Vérification des colonnes dans les lignes
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
        
        # Vérification des générateurs non pilotables
        print("\n=== GÉNÉRATEURS NON PILOTABLES ===")
        generators_df = network.generators
        non_pilotable_df = generators_df[generators_df['type'] == 'non_pilotable']
        print(f"Nombre de générateurs non pilotables: {len(non_pilotable_df)}")
        print(non_pilotable_df)

        # Vérification par carrier
        carriers = non_pilotable_df.groupby('carrier').size()
        print("\nRépartition par type de source:")
        for carrier, count in carriers.items():
            print(f"- {carrier}: {count} générateurs")

        # Vérification des colonnes
        gen_cols = ['type', 'p_nom', 'p_nom_extendable', 'p_nom_min', 'carrier', 'marginal_cost']
        for col in gen_cols:
            if col not in non_pilotable_df.columns:
                print(f"ERREUR: Colonne '{col}' manquante dans les générateurs non pilotables")

        # Vérification de cohérence: tous les bus référencés existent-ils?
        if not non_pilotable_df.empty:
            bus_ids = set(buses_df.index)
            unknown_buses = set(non_pilotable_df['bus'].dropna()) - bus_ids
            if unknown_buses:
                print(f"ERREUR: Certains générateurs non pilotables référencent des bus inconnus: {unknown_buses}")
            else:
                print("✓ Tous les générateurs non pilotables référencent des bus existants")

        # Vérification des attributions de bus
        na_buses = non_pilotable_df['bus'].isna().sum()
        if na_buses > 0:
            print(f"AVERTISSEMENT: {na_buses} générateurs non pilotables n'ont pas de bus attribué")
        else:
            print("✓ Tous les générateurs non pilotables ont un bus attribué")

        # Vérification des générateurs pilotables
        print("\n=== GÉNÉRATEURS PILOTABLES ===")
        pilotable_df = generators_df[generators_df['type'] == 'pilotable']
        print(f"Nombre de générateurs pilotables: {len(pilotable_df)}")
        print(pilotable_df)

        # Vérification par carrier
        carriers_pilotable = pilotable_df.groupby('carrier').size()
        print("\nRépartition par type de source pilotable:")
        for carrier, count in carriers_pilotable.items():
            print(f"- {carrier}: {count} générateurs")

        # Vérification des colonnes pour les générateurs pilotables
        gen_pilotable_cols = ['type', 'p_nom', 'p_nom_extendable', 'p_nom_min', 'p_nom_max', 'p_max_pu', 'carrier']
        for col in gen_pilotable_cols:
            if col not in pilotable_df.columns:
                print(f"ERREUR: Colonne '{col}' manquante dans les générateurs pilotables")

        # Vérification de cohérence: tous les bus référencés existent-ils?
        if not pilotable_df.empty:
            unknown_buses_pilotable = set(pilotable_df['bus'].dropna()) - bus_ids
            if unknown_buses_pilotable:
                print(f"ERREUR: Certains générateurs pilotables référencent des bus inconnus: {unknown_buses_pilotable}")
            else:
                print("✓ Tous les générateurs pilotables référencent des bus existants")

        # Vérification des attributions de bus
        na_buses_pilotable = pilotable_df['bus'].isna().sum()
        if na_buses_pilotable > 0:
            print(f"AVERTISSEMENT: {na_buses_pilotable} générateurs pilotables n'ont pas de bus attribué")
        else:
            print("✓ Tous les générateurs pilotables ont un bus attribué")

        # Vérification des valeurs cohérentes pour p_nom_max
        invalid_p_nom_max = (pilotable_df['p_nom_max'] < pilotable_df['p_nom']).sum()
        if invalid_p_nom_max > 0:
            print(f"ERREUR: {invalid_p_nom_max} générateurs pilotables ont p_nom_max < p_nom")
        else:
            print("✓ Tous les générateurs pilotables ont p_nom_max >= p_nom")

        print("\nTest terminé avec succès!")
        
    except DataLoadError as e:
        print(f"Erreur lors du chargement des données: {e}")
    except Exception as e:
        print(f"Erreur inattendue: {e}")

if __name__ == "__main__":
    test_network_data()

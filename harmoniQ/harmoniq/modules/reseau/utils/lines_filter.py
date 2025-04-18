"""
Module de filtrage et géolocalisation des lignes de transmission.

Gère la lecture des données de lignes, le filtrage des lignes du Québec,
et la géolocalisation des nœuds du réseau électrique.

Contributeurs : Yanis Aksas (yanis.aksas@polymtl.ca)
                Kais Ben Mustapha (kais.ben-mustapha@polymtl.ca)
"""

import pandas as pd
import requests
import time
import os

class LineFilter:
    def __init__(self):
        self.column_names = [
            'transmission_line_id', 'transmission_circuit_id', 'owner', 'province',
            'operating_region', 'number_of_circuits', 'current_type',
            'line_segment_length_km', 'line_segment_length_mi', 'line_length_km',
            'line_length_mi', 'voltage', 'reactance', 'ttc_summer', 'ttc_winter',
            'network_node_name_starting', 'network_node_code_starting',
            'network_node_name_ending', 'network_node_code_ending', 'notes'
        ]

    def _read_excel_file(self, input_file):
        """
        Lit et prépare le fichier Excel
        """
        try:
            df = pd.read_excel(input_file, engine='openpyxl')
            
            if len(df.columns) == 1:
                df = pd.DataFrame([x.split(',') for x in df[df.columns[0]]])
                df = df.iloc[1:].reset_index(drop=True)
                df.columns = self.column_names
            
            df = df.apply(lambda x: x.str.strip('"') if x.dtype == "object" else x)
            return df
            
        except Exception as e:
            print(f"Une erreur est survenue lors de la lecture du fichier : {str(e)}")
            return None

    def filter_quebec_lines(self, input_file, output_file):
        """
        Filtre les lignes de transmission du Québec et les exporte.
        
        Args:
            input_file: Chemin du fichier Excel d'entrée
            output_file: Chemin du fichier CSV de sortie
        """
        df = self._read_excel_file(input_file)
        if df is None:
            return
        
        quebec_df = df[df['province'] == 'QC']
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        quebec_df.to_csv(output_file, index=False, encoding='utf-8')
        
        print(f"Nombre de lignes pour le Québec : {len(quebec_df)}")
        print(f"Fichier sauvegardé : {output_file}")

    def get_unique_nodes(self, input_file, output_file):
        """
        Récupère tous les noms de nœuds uniques (starting et ending) du réseau
        et les sauvegarde dans un fichier CSV.
    
        Args:
            input_file (str): Chemin du fichier d'entrée (CSV ou Excel)
            output_file (str): Chemin du fichier CSV de sortie
        """

        if input_file.endswith('.csv'):
            df = pd.read_csv(input_file)
        else:
            df = self._read_excel_file(input_file)
        
        if df is None:
            return
    
        starting_nodes = df['network_node_name_starting'].unique()
        ending_nodes = df['network_node_name_ending'].unique()
    
        all_nodes = pd.DataFrame({
            'node_name': sorted(list(set(starting_nodes) | set(ending_nodes))),
        })
    
        all_nodes['used_as_start'] = all_nodes['node_name'].isin(starting_nodes)
        all_nodes['used_as_end'] = all_nodes['node_name'].isin(ending_nodes)
    
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
        all_nodes.to_csv(output_file, index=False, encoding='utf-8')
    
        print(f"Nombre total de nœuds uniques : {len(all_nodes)}")
        print(f"Fichier sauvegardé : {output_file}")
    
        stats = {
            'total_nodes': len(all_nodes),
            'starting_nodes': sum(all_nodes['used_as_start']),
            'ending_nodes': sum(all_nodes['used_as_end']),
            'both_nodes': sum(all_nodes['used_as_start'] & all_nodes['used_as_end'])
        }
        

    
    def geolocate_nodes(self, input_nodes_file, output_geolocated_file):
        """
        Géolocalise les nœuds à partir de leurs noms en utilisant l'API Nominatim.
        
        Args:
            input_nodes_file (str): Chemin du fichier CSV contenant les nœuds
            output_geolocated_file (str): Chemin du fichier CSV de sortie avec les coordonnées
        """
        df = pd.read_csv(input_nodes_file)
        
        df['latitude'] = None
        df['longitude'] = None
        
        base_url = "https://nominatim.openstreetmap.org/search"
        headers = {
            'User-Agent': 'PIV',
            'Accept': 'application/json'
        }
        
        print(f"Début de la géolocalisation de {len(df)} nœuds...")
        
        for index, row in df.iterrows():
            node_name = row['node_name']
            
            params = {
                'q':node_name + ", Québec",
                'format': 'json',               
                'limit': 1
            }
            
            try:
                response = requests.get(base_url, params=params, headers=headers)
                
                if response.status_code == 200:
                    results = response.json()
                    
                    if results:
                        df.at[index, 'latitude'] = float(results[0]['lat'])
                        df.at[index, 'longitude'] = float(results[0]['lon'])
                        
                        print(f"Nœud {node_name} géolocalisé : {results[0]['lat']}, {results[0]['lon']}")
                    else:
                        print(f"Aucun résultat trouvé pour le nœud {node_name}")
                
                else:
                    print(f"Erreur lors de la requête pour {node_name}: {response.status_code}")
                
                time.sleep(0.25)
                
            except Exception as e:
                print(f"Erreur lors de la géolocalisation de {node_name}: {str(e)}")
                continue
        
        total_nodes = len(df)
        geolocated_nodes = df['latitude'].notna().sum()
        
        os.makedirs(os.path.dirname(output_geolocated_file), exist_ok=True)
        
        df.to_csv(output_geolocated_file, index=False, encoding='utf-8')
        print(f"\nRésultats sauvegardés dans : {output_geolocated_file}")
            

    def fill_missing_coordinates(self, input_geolocated_file, output_filled_file):
            """
            Remplit les coordonnées manquantes en utilisant la moyenne des coordonnées
            du point précédent et du point suivant dans la liste.
            
            Args:
                input_geolocated_file (str): Chemin du fichier CSV contenant les nœuds géolocalisés
                output_filled_file (str): Chemin du fichier CSV de sortie avec les coordonnées remplies
            """
            df = pd.read_csv(input_geolocated_file)
            
            for index, row in df.iterrows():
                if pd.isna(row['latitude']) or pd.isna(row['longitude']):
                    prev_index = None
                    for i in range(index - 1, -1, -1):
                        if not pd.isna(df.at[i, 'latitude']) and not pd.isna(df.at[i, 'longitude']):
                            prev_index = i
                            break
                    next_index = None
                    for i in range(index + 1, len(df)):
                        if not pd.isna(df.at[i, 'latitude']) and not pd.isna(df.at[i, 'longitude']):
                            next_index = i
                            break
                    if prev_index is not None and next_index is not None:
                        prev_lat = df.at[prev_index, 'latitude']
                        prev_lon = df.at[prev_index, 'longitude']
                        next_lat = df.at[next_index, 'latitude']
                        next_lon = df.at[next_index, 'longitude']
                        
                        if not pd.isna(prev_lat) and not pd.isna(next_lat):
                            df.at[index, 'latitude'] = (prev_lat + next_lat) / 2
                        if not pd.isna(prev_lon) and not pd.isna(next_lon):
                            df.at[index, 'longitude'] = (prev_lon + next_lon) / 2
            
            os.makedirs(os.path.dirname(output_filled_file), exist_ok=True)
            
            df.to_csv(output_filled_file, index=False, encoding='utf-8')
            print(f"Résultats avec coordonnées remplies sauvegardés dans : {output_filled_file}")


if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    input_file = os.path.join(project_root, "data", "topology", "transmission_lines.xlsx")
    output_quebec_file = os.path.join(project_root, "data", "topology", "lignes_quebec.csv")
    output_nodes_file = os.path.join(project_root, "data", "topology", "unique_nodes.csv")
    output_geolocated_file = os.path.join(project_root, "data", "topology", "geolocated_nodes.csv")
    output_filled_file = os.path.join(project_root, "data", "topology", "filled_geolocated_nodes.csv")
    
    line_filter = LineFilter()
    
    # # Exécuter le filtrage des lignes du Québec
    # line_filter.filter_quebec_lines(input_file, output_quebec_file)
    
    # # Exporter les nœuds uniques
    # line_filter.get_unique_nodes(output_quebec_file, output_nodes_file)

    # line_filter.geolocate_nodes(output_nodes_file, output_geolocated_file )

     # Remplir les coordonnées manquantes
    line_filter.fill_missing_coordinates(output_geolocated_file, output_filled_file)
#import geopandas as gpd
#import matplotlib.pyplot as plt

# Charger le fichier Shapefile
#shapefile_path = "officiel/data/MRC_GROUPE_9/base_mrc_database.shp"
#gdf = gpd.read_file(shapefile_path)

# Afficher un aperçu des données
#print(gdf.head())

# Créer la carte
#fig, ax = plt.subplots(figsize=(10, 8))
#gdf.plot(ax=ax, edgecolor="black", cmap="viridis") 
#ax.set_title("Carte des MRC", fontsize=14)

#plt.show()

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import matplotlib.pyplot as plt

# Charger le fichier Shapefile des MRC
shapefile_path = "officiel/data/MRC_GROUPE_9/base_mrc_database.shp"
gdf_mrc = gpd.read_file(shapefile_path)

# Charger le fichier CSV contenant les points
csv_file_path = "officiel/data/topology/filled_geolocated_nodes.csv"
df_points = pd.read_csv(csv_file_path)

# Charger le fichier CSV contenant les noms des MRC
mrc_names_file_path = "officiel/data/MRC_GROUPE_9/coordonnees_MRC.csv"
df_mrc_names = pd.read_csv(mrc_names_file_path)

# Créer un dictionnaire de mappage des ID des MRC aux noms des MRC
mrc_names_dict = pd.Series(df_mrc_names.CDNAME.values, index=df_mrc_names.ID).to_dict()

# Filtrer les points valides (ceux qui ont des coordonnées non nulles)
df_points_valid = df_points.dropna(subset=['latitude', 'longitude'])

# Convertir les points valides en GeoDataFrame
geometry = [Point(xy) for xy in zip(df_points_valid['longitude'], df_points_valid['latitude'])]
gdf_points = gpd.GeoDataFrame(df_points_valid, geometry=geometry)

# Effectuer une jointure spatiale pour trouver à quelle MRC appartiennent les points
gdf_points_in_mrc = gpd.sjoin(gdf_points, gdf_mrc, how="inner", predicate="within")

# Filtrer les points qui n'appartiennent pas aux MRC
gdf_points_not_in_mrc = gdf_points[~gdf_points.index.isin(gdf_points_in_mrc.index)]

# Afficher les points qui n'appartiennent pas aux MRC avec leurs coordonnées
print("\nPoints qui n'appartiennent pas aux MRC:")
pd.set_option('display.max_rows', None)
print(gdf_points_not_in_mrc[['node_name', 'latitude', 'longitude']])

# Grouper les points par MRC et afficher les résultats
mrc_points = gdf_points_in_mrc.groupby('index_right').apply(lambda x: x[['node_name', 'latitude', 'longitude']].to_dict(orient='records'))

print("\nListe des MRC et des points qui les composent:")
for mrc_id, points in mrc_points.items():
    mrc_name = mrc_names_dict.get(mrc_id)  # Utiliser le dictionnaire pour obtenir le nom du MRC
    print(f"\n{mrc_id}, {mrc_name}")
    for point in points:
        print(f"  Point: {point['node_name']}, Latitude: {point['latitude']}, Longitude: {point['longitude']}")


# Filtrer les points où used_as_end est True, used_as_start est True, et les deux
df_points_end = gdf_points_in_mrc[gdf_points_in_mrc['used_as_end'] == True]
df_points_start = gdf_points_in_mrc[gdf_points_in_mrc['used_as_start'] == True]
df_points_both = gdf_points_in_mrc[(gdf_points_in_mrc['used_as_end'] == True) & (gdf_points_in_mrc['used_as_start'] == True)]

# Afficher les points avec leurs coordonnées
#print("\nPoints utilisés comme fin:")
#print(df_points_end[['node_name', 'latitude', 'longitude']])

#print("\nPoints utilisés comme début:")
#print(df_points_start[['node_name', 'latitude', 'longitude']])

#print("\nPoints utilisés comme début et fin:")
#print(df_points_both[['node_name', 'latitude', 'longitude']])

# Tracer les points sur la carte des MRC
fig, ax = plt.subplots(figsize=(10, 8))
gdf_mrc.plot(ax=ax, edgecolor="black", cmap="viridis")

# Points utilisés comme fin (rouge)
df_points_end.plot(ax=ax, color='red', markersize=5, label='End')

# Points utilisés comme début (bleu)
df_points_start.plot(ax=ax, color='blue', markersize=5, label='Start')

# Points utilisés comme début et fin (vert)
df_points_both.plot(ax=ax, color='green', markersize=5, label='Start and End')

ax.set_title("Carte des MRC avec Points")
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.legend()
plt.show()
import geopandas as gpd
import matplotlib.pyplot as plt

# Charger le fichier Shapefile
shapefile_path = "officiel/data/MRC_GROUPE_9/base_mrc_database.shp"
gdf = gpd.read_file(shapefile_path)

# Afficher un aperçu des données
print(gdf.head())

# Créer la carte
fig, ax = plt.subplots(figsize=(10, 8))
gdf.plot(ax=ax, edgecolor="black", cmap="viridis") 
ax.set_title("Carte des MRC", fontsize=14)

plt.show()

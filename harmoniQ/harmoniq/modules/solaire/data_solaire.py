import pandas as pd
import numpy as np
# data_solaire.py

# Définition des centrales solaires avec leurs puissances
coordinates_centrales = [
    (45.4167, -73.4999, "La Prairie", 0, "Etc/GMT+5", 8000),  # 8 MW = 8000 kW
    (45.6833, -73.4333, "Varennes", 0, "Etc/GMT+5", 1500),  # 1.5 MW = 1500 kW
]
coordinates_residential = [
    (48.4808, -68.5210, "Bas-Saint-Laurent", 0, "Etc/GMT+5"),
    (48.4284, -71.0683, "Saguenay-Lac-Saint-Jean", 0, "Etc/GMT+5"),
    (46.8139, -71.2082, "Capitale-Nationale", 0, "Etc/GMT+5"),
    (46.3420, -72.5477, "Mauricie", 0, "Etc/GMT+5"),
    (45.4036, -71.8826, "Estrie", 0, "Etc/GMT+5"),
    (45.5017, -73.5673, "Montreal", 0, "Etc/GMT+5"),
    (45.4215, -75.6919, "Outaouais", 0, "Etc/GMT+5"),
    (48.0703, -77.7600, "Abitibi-Temiscamingue", 0, "Etc/GMT+5"),
    (50.0340, -66.9141, "Cote-Nord", 0, "Etc/GMT+5"),
    (53.4667, -76.0000, "Nord-du-Quebec", 0, "Etc/GMT+5"),
    (48.8360, -64.4931, "Gaspesie–Iles-de-la-Madeleine", 0, "Etc/GMT+5"),
    (46.5000, -70.9000, "Chaudiere-Appalaches", 0, "Etc/GMT+5"),
    (45.6066, -73.7124, "Laval", 0, "Etc/GMT+5"),
    (46.0270, -73.4360, "Lanaudiere", 0, "Etc/GMT+5"),
    (45.9990, -74.1428, "Laurentides", 0, "Etc/GMT+5"),
    (45.4500, -73.3496, "Monteregie", 0, "Etc/GMT+5"),
    (46.4043, -72.0169, "Centre-du-Quebec", 0, "Etc/GMT+5"),
]

population_relative = {
    "Bas-Saint-Laurent": 0.0226,
    "Saguenay-Lac-Saint-Jean": 0.0317,
    "Capitale-Nationale": 0.0897,
    "Mauricie": 0.0318,
    "Estrie": 0.0580,
    "Montreal": 0.2430,
    "Outaouais": 0.0472,
    "Abitibi-Temiscamingue": 0.0165,
    "Cote-Nord": 0.0099,
    "Nord-du-Quebec": 0.0052,
    "Gaspesie–Iles-de-la-Madeleine": 0.0102,
    "Chaudiere-Appalaches": 0.0503,
    "Laval": 0.0508,
    "Lanaudiere": 0.0620,
    "Laurentides": 0.0744,
    "Monteregie": 0.1675,
    "Centre-du-Quebec": 0.0291,
}
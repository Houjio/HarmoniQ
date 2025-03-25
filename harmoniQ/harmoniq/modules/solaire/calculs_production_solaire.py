import pvlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time


def get_weather_data(coordinates_residential):
    """
    Récupère les données météorologiques pour les emplacements spécifiés.

    Parameters
    ----------
    coordinates : list of tuples
        Liste des coordonnées des emplacements sous forme de tuples (latitude, longitude, nom, altitude, fuseau horaire).

    Returns
    -------
    list of DataFrame
        Liste des DataFrames contenant les données météorologiques pour chaque emplacement.
    """
    tmys = []
    for location in coordinates_residential:
        latitude, longitude, name, altitude, timezone = location
        print(f"\nRécupération des données météo pour {name}...")
        weather = pvlib.iotools.get_pvgis_tmy(latitude, longitude)[0]
        weather.index.name = "utc_time"
        tmys.append(weather)
    return tmys


def calculate_solar_parameters(
    weather,
    latitude,
    longitude,
    altitude,
    temperature_model_parameters,
    module,
    inverter,
    surface_tilt,
    surface_orientation,
):
    """
    Calcule les paramètres solaires et l'irradiance pour un emplacement donné.

    Parameters
    ----------
    weather : DataFrame
        Données météorologiques pour l'emplacement.
    latitude : float
        Latitude de l'emplacement.
    longitude : float
        Longitude de l'emplacement.
    altitude : float
        Altitude de l'emplacement en mètres.
    temperature_model_parameters : dict
        Paramètres du modèle de température.
    module : dict
        Paramètres du module solaire.
    inverter : dict
        Paramètres de l'onduleur.
    surface_tilt : float
        Angle d'inclinaison des panneaux solaires.
    surface_azimuth : float
        Orientation des panneaux solaires.

    Returns
    -------
    Series
        Puissance AC calculée pour chaque pas de temps.
    """
    solpos = pvlib.solarposition.get_solarposition(
        time=weather.index,
        latitude=latitude,
        longitude=longitude,
        altitude=altitude,
        temperature=weather["temp_air"],
        pressure=pvlib.atmosphere.alt2pres(altitude),
    )
    dni_extra = pvlib.irradiance.get_extra_radiation(weather.index)
    airmass = pvlib.atmosphere.get_relative_airmass(solpos["apparent_zenith"])
    pressure = pvlib.atmosphere.alt2pres(altitude)
    am_abs = pvlib.atmosphere.get_absolute_airmass(airmass, pressure)
    aoi = pvlib.irradiance.aoi(
        surface_tilt,
        surface_orientation,
        solpos["apparent_zenith"],
        solpos["azimuth"],
    )
    total_irradiance = pvlib.irradiance.get_total_irradiance(
        surface_tilt,
        surface_orientation,
        solpos["apparent_zenith"],
        solpos["azimuth"],
        weather["dni"],
        weather["ghi"],
        weather["dhi"],
        dni_extra=dni_extra,
        model="haydavies",
    )
    cell_temperature = pvlib.temperature.sapm_cell(
        total_irradiance["poa_global"],
        weather["temp_air"],
        weather["wind_speed"],
        **temperature_model_parameters,
    )
    effective_irradiance = pvlib.pvsystem.sapm_effective_irradiance(
        total_irradiance["poa_direct"],
        total_irradiance["poa_diffuse"],
        am_abs,
        aoi,
        module,
    )
    dc = pvlib.pvsystem.sapm(effective_irradiance, cell_temperature, module)
    ac = pvlib.inverter.sandia(dc["v_mp"], dc["p_mp"], inverter)
    print(inverter)
    return 

def convert_solar(value, module, mode="surface_to_power"):
    """
    Convertit une surface disponible en puissance installée ou une puissance souhaitée en superficie nécessaire en utilisant les paramètres du module solaire.

    Parameters
    ----------
    value : float
        Surface disponible en mètres carrés (m²) ou puissance souhaitée en kilowatts (kW).
    module : pandas.Series
        Paramètres du module solaire.
    mode : str, optional
        Mode de conversion, soit 'surface_to_power' pour convertir une surface en puissance, soit 'power_to_surface' pour convertir une puissance en surface. Par défaut 'surface_to_power'.

    Returns
    -------
    float
        Puissance installée en kilowatts (kW) ou superficie nécessaire en mètres carrés (m²).
    """
    # Efficacité du module solaire
    panel_efficiency = module["Impo"] * module["Vmpo"] / (1000 * module["Area"])

    if mode == "surface_to_power":
        # Calcul de la puissance installée en watts (W)
        power_w = value * panel_efficiency * 1000
        # Conversion de la puissance en kilowatts (kW)
        power_kw = power_w / 1000
        return power_kw
    elif mode == "power_to_surface":
        # Calcul de la superficie nécessaire en mètres carrés (m²)
        surface_m2 = value * 1000 / (panel_efficiency * 1000)
        return surface_m2
    else:
        raise ValueError(
            "Mode invalide. Utilisez 'surface_to_power' ou 'power_to_surface'."
        )


# Initialisation des modèles solaires
start_time = time.time()
sandia_modules = pvlib.pvsystem.retrieve_sam("SandiaMod")
module = sandia_modules["Canadian_Solar_CS5P_220M___2009_"]

# Exemple d'utilisation de la fonction convert_solar
surface_m2 = 100  # Surface disponible en m²
power_kw = convert_solar(surface_m2, module, mode="surface_to_power")
print("\n--Conversion surface_to_power--")
print(f"Surface disponible : {surface_m2} m²")
print(f"Puissance installée : {power_kw:.2f} kW")

desired_power_kw = 10  # Puissance souhaitée en kW
required_surface_m2 = convert_solar(desired_power_kw, module, mode="power_to_surface")
print("\n--Conversion power_to_surface--")
print(f"Puissance souhaitée : {desired_power_kw} kW")
print(f"Superficie nécessaire : {required_surface_m2:.2f} m²")

# Définition des centrales solaires avec leurs puissances
coordinates_centrales = [
    (45.4167, -73.4999, "La Prairie", 0, "Etc/GMT+5", 8000),  # 8 MW = 8000 kW
    (45.6833, -73.4333, "Varennes", 0, "Etc/GMT+5", 1500),  # 1.5 MW = 1500 kW
]


def calculate_energy_solar_plants(
    coordinates_centrales, surface_tilt=45, surface_orientation=180
):
    """
    Calcule la production d'énergie annuelle pour des centrales solaires
    aux coordonnées données avec leurs puissances spécifiées.

    Parameters
    ----------
    coordinates_centrales : tuple
        Tuple contenant (latitude, longitude, nom, altitude, timezone, puissance_kw)
    surface_tilt : float, optional
        Angle d'inclinaison des panneaux en degrés. Par défaut 30°
    surface_orientation : float, optional
        Orientation des panneaux en degrés (180° = sud). Par défaut 180°

    Returns
    -------
    dict
        Dictionnaire contenant l'énergie annuelle (Wh) et les données horaires pour chaque centrale
    """
    # Initialisation des modèles
    sandia_modules = pvlib.pvsystem.retrieve_sam("SandiaMod")
    sapm_inverters = pvlib.pvsystem.retrieve_sam("cecinverter")

    module = sandia_modules["Canadian_Solar_CS5P_220M___2009_"]
    inverter = sapm_inverters["ABB__MICRO_0_25_I_OUTD_US_208__208V_"]
    temperature_model_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS[
        "sapm"
    ]["open_rack_glass_glass"]

    resultats_centrales = {}
    energie_totale = 0

    for centrale in coordinates_centrales:
        latitude, longitude, name, altitude, timezone, puissance_kw = centrale

        # Récupération des données météo
        print(f"\nRécupération des données météo pour {name}...")
        weather = pvlib.iotools.get_pvgis_tmy(latitude, longitude)[0]
        weather.index.name = "utc_time"

        # Calcul du nombre de modules nécessaires
        puissance_module_w = module["Impo"] * module["Vmpo"]
        nombre_modules = int(np.ceil((puissance_kw * 1000) / puissance_module_w))

        # Calcul de la production
        print(f"Calcul de la production pour {name} ({puissance_kw} kW)...")
        ac = calculate_solar_parameters(
            weather,
            latitude,
            longitude,
            altitude,
            temperature_model_parameters,
            module,
            inverter,
            surface_tilt,
            surface_orientation,
        )

        # Mise à l'échelle selon la puissance de la centrale
        ac_scaled = ac * nombre_modules
        annual_energy = ac_scaled.sum()
        energie_totale += annual_energy

        # Stockage des résultats pour cette centrale
        resultats_centrales[name] = {
            "energie_annuelle_wh": annual_energy,
            "energie_horaire": ac_scaled,
            "nombre_modules": nombre_modules,
            "puissance_kw": puissance_kw,
        }

        print(f"\nRésultats pour {name}:")
        print(f"Puissance installée : {puissance_kw} kW")
        print(f"Nombre de modules : {nombre_modules}")
        print(f"Production annuelle : {annual_energy/1000:.2f} kWh")

    resultats_centrales["energie_totale_wh"] = energie_totale
    return resultats_centrales


# Utilisation de la fonction
resultats_centrales = calculate_energy_solar_plants(coordinates_centrales)
energie_centrales = resultats_centrales["energie_totale_wh"]


def calculate_regional_residential_solar(
    coordinates_residential: List[tuple],
    population_relative,
    total_clients,
    num_panels_per_client,
    surface_tilt,
    surface_orientation,
):
    """
    Calcule la production d'énergie solaire résidentielle potentielle par région administrative.

    Parameters
    ----------
    coordinates_residential : list of tuples
        Liste des coordonnées des régions sous forme de tuples
        (latitude, longitude, nom, altitude, timezone)
    population_relative : dict
        Dictionnaire contenant la population relative pour chaque région.
    total_clients : int
        Nombre total de clients subventionnés.
    num_panels_per_client : int, optional
        Nombre de panneaux par client. Par défaut 4.
    surface_tilt : float, optional
        Angle d'inclinaison des panneaux en degrés. Par défaut 30°
    surface_azimuth : float, optional
        Orientation des panneaux en degrés (180° = sud). Par défaut 180°

    Returns
    -------
    dict
        Dictionnaire contenant pour chaque région:
        - énergie annuelle (kWh)
        - puissance installée (kW)
        - surface installée (m²)
        - coordonnées (lat, lon)
    """

    # Initialisation des modèles
    sandia_modules = pvlib.pvsystem.retrieve_sam("SandiaMod")
    module = sandia_modules["Canadian_Solar_CS5P_220M___2009_"]

    resultats_regions = {}

    for coordinates in coordinates_residential:
        latitude, longitude, nom_region, altitude, timezone = coordinates
        population_weight = population_relative.get(nom_region, 0)
        num_clients_region = total_clients * population_weight
        surface_panneau_region = (
            num_clients_region * num_panels_per_client * module["Area"]
        )

        # Conversion de la surface en puissance
        puissance_installee_kw = convert_solar(
            surface_panneau_region, module, mode="surface_to_power"
        )

        print(
            f"\nCalcul pour la région {nom_region} avec une surface de {surface_panneau_region:.2f} m² ({puissance_installee_kw:.2f} kW)..."
        )

        # Création du tuple de coordonnées avec la puissance
        coordinates_with_power = (
            latitude,
            longitude,
            nom_region,
            altitude,
            timezone,
            puissance_installee_kw,
        )

        # Calcul de la production d'énergie
        production = calculate_energy_solar_plants(
            [coordinates_with_power],  # Liste avec un seul tuple de coordonnées
            surface_tilt=surface_tilt,
            surface_orientation=surface_orientation,
        )

        # Récupération des résultats pour cette région
        region_results = production[nom_region]

        # Stockage des résultats
        resultats_regions[nom_region] = {
            "energie_annuelle_kwh": region_results["energie_annuelle_wh"] / 1000,
            "puissance_installee_kw": puissance_installee_kw,
            "surface_installee_m2": surface_panneau_region,
            "latitude": latitude,
            "longitude": longitude,
        }

        print(f"Résultats pour {nom_region}:")
        print(f"Surface installée: {surface_panneau_region:.2f} m²")
        print(f"Puissance installée: {puissance_installee_kw:.2f} kW")
        print(
            f"Production annuelle: {region_results['energie_annuelle_wh']/1000:,.2f} kWh"
        )

    return resultats_regions


def cost_solar_powerplant(coordinates_centrales, resultats_centrales):
    """
    Calcule le coût total pour chaque centrale solaire.

    Parameters
    ----------
    coordinates_centrales : list of tuples
        Liste des coordonnées et puissances des centrales
    resultats_centrales : dict
        Dictionnaire contenant l'énergie produite par chaque centrale

    Returns
    -------
    dict
        Dictionnaire contenant le coût total en dollars pour chaque centrale
    """
    couts = {}

    for centrale in coordinates_centrales:
        nom = centrale[2]
        puissance_mw = centrale[5] / 1000  # Conversion kW en MW

        # Coût de référence par MW pour le Québec
        cout_par_mw = 4_210_000  # Estimation moyenne des coûts actuels

        # Coût total prenant en compte les coûts indirects et opérationnels
        cout_total = puissance_mw * cout_par_mw

        couts[nom] = cout_total

    return couts


def calculate_installation_cost(coordinates_centrales):
    """
    Calcule le coût d'installation pour chaque centrale solaire avec une estimation plus précise.

    Parameters
    ----------
    coordinates_centrales : list of tuples
        Liste des coordonnées et puissances des centrales

    Returns
    -------
    dict
        Dictionnaire contenant le coût d'installation pour chaque centrale
    """
    couts_installation = {}

    for centrale in coordinates_centrales:
        nom = centrale[2]
        puissance_mw = centrale[5] / 1000  # Conversion kW en MW

        # Coûts de base par MW selon la taille de l'installation
        if puissance_mw < 1:
            cout_base = 4_500_000  # Plus cher pour petites installations
        elif 1 <= puissance_mw < 5:
            cout_base = 4_210_000  # Coût moyen
        else:
            cout_base = 3_900_000  # Économies d'échelle pour grandes installations

        # Facteurs d'ajustement
        facteur_echelle = 0.85  # Économies d'échelle
        facteur_complexite = 1.1  # Complexité du site et infrastructure

        # Calcul du coût d'installation avec facteurs
        cout_installation = (
            cout_base * (puissance_mw**facteur_echelle) * facteur_complexite
        )

        couts_installation[nom] = cout_installation

    return couts_installation


def calculate_lifetime(coordinates_centrales):
    """
    Estime la durée de vie des centrales solaires en fonction de leurs puissances installées.

    Parameters
    ----------
    coordinates_centrales : list of tuples
        Liste des coordonnées et puissances des centrales sous forme de tuples
        (latitude, longitude, nom, altitude, timezone, puissance_kw)

    Returns
    -------
    dict
        Dictionnaire contenant la durée de vie estimée pour chaque centrale
    """
    durees_vie = {}

    for centrale in coordinates_centrales:
        nom = centrale[2]
        puissance_mw = centrale[5] / 1000  # Conversion kW en MW

        if puissance_mw < 1:
            duree_vie = 25  # Petites installations
        elif 1 <= puissance_mw < 10:
            duree_vie = 30  # Installations moyennes
        else:
            duree_vie = 35  # Grandes installations

        durees_vie[nom] = duree_vie

    return durees_vie


def co2_emissions_solar(
    coordinates_centrales, resultats_centrales, facteur_emission=40
):
    """
    Calcule les émissions totales de CO₂ équivalent pour chaque centrale solaire sur toute sa durée de vie.

    Parameters
    ----------
    coordinates_centrales : list of tuples
        Liste des coordonnées et puissances des centrales
    resultats_centrales : dict
        Dictionnaire contenant l'énergie produite par chaque centrale
    facteur_emission : float, optional
        Facteur d'émission en g CO₂eq/kWh basé sur l'ACV

    Returns
    -------
    dict
        Dictionnaire contenant les émissions totales de CO₂ en kg pour chaque centrale
    """
    emissions = {}
    durees_vie = calculate_lifetime(coordinates_centrales)

    for centrale in coordinates_centrales:
        nom = centrale[2]
        energie_kwh = resultats_centrales[nom]["energie_annuelle_wh"] / 1000
        duree_vie = durees_vie[nom]

        # Calcul des émissions sur toute la durée de vie
        emissions_g = energie_kwh * facteur_emission * duree_vie
        emissions[nom] = emissions_g / 1000

    return emissions


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

# Utilisation des fonctions
couts = cost_solar_powerplant(coordinates_centrales, resultats_centrales)
couts_installation = calculate_installation_cost(coordinates_centrales)
durees_vie = calculate_lifetime(coordinates_centrales)
emissions_co2 = co2_emissions_solar(coordinates_centrales, resultats_centrales)

# Affichage des résultats
print("\n=== RÉSULTATS PAR CENTRALE ===")
for centrale in coordinates_centrales:
    nom = centrale[2]
    duree_vie = durees_vie[nom]
    print(f"\n{nom}:")
    print(
        f"  Production annuelle : {resultats_centrales[nom]['energie_annuelle_wh']/1000:,.2f} kWh"
    )
    print(f"  Puissance installée : {centrale[5]:,.2f} kW")
    print(f"  Coût total : {couts[nom]:,.2f} $")
    print(f"  Coût d'installation : {couts_installation[nom]:,.2f} $")
    print(f"  Durée de vie estimée : {duree_vie} ans")
    print(
        f"  Émissions CO₂ totales : {emissions_co2[nom]:,.2f} kg CO₂eq sur {duree_vie} ans"
    )

end_time = time.time()

print(f"\nTemps d'exécution : {end_time - start_time:.2f} secondes")


# Exemple d'utilisation
if __name__ == "__main__":
    # Test avec une surface de 100 m²
    surface_test = 100  # m²

    print("\nDébut des calculs pour toutes les régions du Québec...")
    resultats = calculate_regional_residential_solar(
        coordinates_residential,
        population_relative,
        total_clients=125000,
        num_panels_per_client=4,
        surface_tilt=0,
        surface_orientation=180,
    )

    # Affichage du résumé des résultats
    print("\n=== RÉSUMÉ DES RÉSULTATS POUR TOUTES LES RÉGIONS ===")
    energie_totale = 0
    for nom_region, data in resultats.items():
        energie_totale += data["energie_annuelle_kwh"]
        print(f"\n{nom_region}:")
        print(f"  Production annuelle : {data['energie_annuelle_kwh']:,.2f} kWh")
        print(f"  Surface installée : {data['surface_installee_m2']:.2f} m²")
        print(f"  Puissance installée : {data['puissance_installee_kw']:.2f} kW")

    print(f"\nProduction totale pour toutes les régions : {energie_totale:,.2f} kWh")


#   Validation avec données réelles Hydro-Québec
def load_csv(file_path):
    """
    Charge le fichier CSV contenant les données de production solaire.

    Parameters
    ----------
    file_path : str
        Chemin vers le fichier CSV.

    Returns
    -------
    DataFrame
        DataFrame contenant les données de production solaire.
    """
    return pd.read_csv(file_path, sep=";")


def plot_validation(resultats_centrales, real_data):
    """
    Superpose sur un graphique mensuel la production des centrales solaires simulée totale avec les données réelles.

    Parameters
    ----------
    resultats_centrales : dict
        Dictionnaire contenant les résultats des centrales solaires simulées.
    real_data : DataFrame
        DataFrame contenant les données de production solaire réelle.
    """
    # Combiner les données horaires de toutes les centrales simulées
    simulated_data = pd.concat(
        [
            resultats_centrales[name]["energie_horaire"]
            for name in resultats_centrales.keys()
            if name != "energie_totale_wh"
        ]
    )
    simulated_data = simulated_data.groupby(simulated_data.index).sum()

    # Assurez-vous que simulated_data est un DataFrame et ajoutez la colonne 'production_kwh'
    simulated_data = simulated_data.to_frame(name="production_kwh")
    simulated_data["month"] = simulated_data.index.month

    # Calculer la production mensuelle simulée
    monthly_simulated = (
        simulated_data.groupby("month")["production_kwh"].sum() / 1e6
    )  # Conversion de Wh en MWh

    real_data["Solaire"] = real_data["Solaire"]

    # Calculer la production mensuelle réelle
    real_data["month"] = pd.to_datetime(real_data["Date"]).dt.month
    monthly_real = real_data.groupby("month")["Solaire"].sum()
    # Tracer le graphique
    plt.figure(figsize=(10, 6))
    plt.plot(
        monthly_simulated.index,
        monthly_simulated.values,
        marker="o",
        linestyle="-",
        color="b",
        label="Production simulée",
    )
    plt.plot(
        monthly_real.index,
        monthly_real.values,
        marker="o",
        linestyle="-",
        color="r",
        label="Production réelle",
    )
    plt.title("Production Solaire Mensuelle")
    plt.xlabel("Mois")
    plt.ylabel("Production (MWh)")
    plt.legend()
    plt.grid(True)
    plt.xticks(range(1, 13))
    plt.show()


# Charger les données réelles
file_path = "2022-sources-electricite-quebec.csv"
real_data = load_csv(file_path)

# Superposer les données simulées et réelles sur un graphique
plot_validation(resultats_centrales, real_data)

end_time = time.time()
print(f"\nTemps d'exécution : {end_time - start_time:.2f} secondes")

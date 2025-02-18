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

def calculate_solar_parameters(weather, latitude, longitude, altitude, temperature_model_parameters, module, inverter, surface_tilt, surface_orientation):
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
    airmass = pvlib.atmosphere.get_relative_airmass(solpos['apparent_zenith'])
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
        solpos['apparent_zenith'],
        solpos['azimuth'],
        weather['dni'],
        weather['ghi'],
        weather['dhi'],
        dni_extra=dni_extra,
        model='haydavies',
    )
    cell_temperature = pvlib.temperature.sapm_cell(
        total_irradiance['poa_global'],
        weather["temp_air"],
        weather["wind_speed"],
        **temperature_model_parameters,
    )
    effective_irradiance = pvlib.pvsystem.sapm_effective_irradiance(
        total_irradiance['poa_direct'],
        total_irradiance['poa_diffuse'],
        am_abs,
        aoi,
        module,
    )
    dc = pvlib.pvsystem.sapm(effective_irradiance, cell_temperature, module)
    ac = pvlib.inverter.sandia(dc['v_mp'], dc['p_mp'], inverter)
    return ac


def convert_solar(value, module, mode='surface_to_power'):
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
    panel_efficiency = module['Impo'] * module['Vmpo'] / (1000 * module['Area'])
    
    if mode == 'surface_to_power':
        # Calcul de la puissance installée en watts (W)
        power_w = value * panel_efficiency * 1000
        # Conversion de la puissance en kilowatts (kW)
        power_kw = power_w / 1000
        return power_kw
    elif mode == 'power_to_surface':
        # Calcul de la superficie nécessaire en mètres carrés (m²)
        surface_m2 = value * 1000 / (panel_efficiency * 1000)
        return surface_m2
    else:
        raise ValueError("Mode invalide. Utilisez 'surface_to_power' ou 'power_to_surface'.")

# Initialisation des modèles solaires
start_time = time.time()
sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
module = sandia_modules['Canadian_Solar_CS5P_220M___2009_']

# Exemple d'utilisation de la fonction convert_solar
surface_m2 = 100  # Surface disponible en m²
power_kw = convert_solar(surface_m2, module, mode='surface_to_power')
print("\n--Conversion surface_to_power--")
print(f"Surface disponible : {surface_m2} m²")
print(f"Puissance installée : {power_kw:.2f} kW")

desired_power_kw = 10  # Puissance souhaitée en kW
required_surface_m2 = convert_solar(desired_power_kw, module, mode='power_to_surface')
print("\n--Conversion power_to_surface--")
print(f"Puissance souhaitée : {desired_power_kw} kW")
print(f"Superficie nécessaire : {required_surface_m2:.2f} m²")

def calculate_energy_solar_plants(coordinates_centrales, puissance_kw, surface_tilt=30, surface_orientation=180):
    """
    Calcule la production d'énergie annuelle pour une installation solaire 
    de puissance spécifiée à des coordonnées données.

    Parameters
    ----------
    coordinates : tuple
        Tuple contenant (latitude, longitude, nom, altitude, timezone)
    puissance_kw : float
        Puissance crête souhaitée en kilowatts (kW)
    surface_tilt : float, optional
        Angle d'inclinaison des panneaux en degrés. Par défaut 30°
    surface_orientation : float, optional
        Orientation des panneaux en degrés (180° = sud). Par défaut 180°

    Returns
    -------
    dict
        Dictionnaire contenant l'énergie annuelle (Wh) et les données horaires
    """
    # Initialisation des modèles
    sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')
    
    # Sélection du module et de l'onduleur
    module = sandia_modules['Canadian_Solar_CS5P_220M___2009_']
    inverter = sapm_inverters['ABB__MICRO_0_25_I_OUTD_US_208__208V_']
    
    # Paramètres thermiques
    temperature_model_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']
    
    # Extraction des coordonnées
    latitude, longitude, name, altitude, timezone = coordinates_centrales
    
    # Récupération des données météo
    print(f"\nRécupération des données météo pour {name}...")
    weather = pvlib.iotools.get_pvgis_tmy(latitude, longitude)[0]
    weather.index.name = "utc_time"
    
    # Calcul du nombre de modules nécessaires
    puissance_module_w = module['Impo'] * module['Vmpo']
    nombre_modules = int(np.ceil((puissance_kw * 1000) / puissance_module_w))
    
    # Calcul de la production
    print(f"Calcul de la production pour {puissance_kw} kW...")
    ac = calculate_solar_parameters(
        weather, latitude, longitude, altitude,
        temperature_model_parameters, module, inverter,
        surface_tilt, surface_orientation
    )
    
    # Mise à l'échelle selon la puissance demandée
    ac_scaled = ac * nombre_modules
    annual_energy = ac_scaled.sum()
    
    print(f"\nRésultats pour {name}:")
    print(f"Puissance installée : {puissance_kw} kW")
    print(f"Nombre de modules : {nombre_modules}")
    print(f"Production annuelle : {annual_energy/1000:.2f} kWh")
    
    return {
        'energie_annuelle_wh': annual_energy,
        'energie_horaire': ac_scaled,
        'nombre_modules': nombre_modules
    }
energie_centrales = calculate_energy_solar_plants((46.81, -71.25, 'Varennes', 10, 'Etc/GMT+5'), 9500)['energie_annuelle_wh']

def calculate_regional_residential_solar(coordinates_residential, population_relative, total_clients=125000, num_panels_per_client=4, surface_tilt=0, surface_orientation=180):
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

    population_relative = {
        "Bas-Saint-Laurent": 0.0226,
        "Saguenay-Lac-Saint-Jean": 0.0317,
        "Capitale-Nationale": 0.0897,
        "Mauricie": 0.0318,
        "Estrie": 0.0580,
        "Montréal": 0.2430,
        "Outaouais": 0.0472,
        "Abitibi-Témiscamingue": 0.0165,
        "Côte-Nord": 0.0099,
        "Nord-du-Québec": 0.0052,
        "Gaspésie-Îles-de-la-Madeleine": 0.0102,
        "Chaudière-Appalaches": 0.0503,
        "Laval": 0.0508,
        "Lanaudière": 0.0620,
        "Laurentides": 0.0744,
        "Montérégie": 0.1675,
        "Centre-du-Québec": 0.0291
    }
    
    # Initialisation des modèles
    sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
    module = sandia_modules['Canadian_Solar_CS5P_220M___2009_']
    
    resultats_regions = {}
    
    for coordinates in coordinates_residential:
        latitude, longitude, nom_region, altitude, timezone = coordinates
        population_weight = population_relative.get(nom_region, 0)
        num_clients_region = total_clients * population_weight
        surface_panneau_region = num_clients_region * num_panels_per_client * module['Area']
        
        # Conversion de la surface en puissance
        puissance_installee_kw = convert_solar(surface_panneau_region, module, mode='surface_to_power')
        
        print(f"\nCalcul pour la région {nom_region} avec une surface de {surface_panneau_region:.2f} m² ({puissance_installee_kw:.2f} kW)...")
        
        # Calcul de la production d'énergie
        production = calculate_energy_solar_plants(
            coordinates, 
            puissance_installee_kw,
            surface_tilt=surface_tilt,
            surface_orientation=surface_orientation
        )
        
        # Stockage des résultats
        resultats_regions[nom_region] = {
            'energie_annuelle_kwh': production['energie_annuelle_wh'] / 1000,
            'puissance_installee_kw': puissance_installee_kw,
            'surface_installee_m2': surface_panneau_region,
            'latitude': latitude,
            'longitude': longitude
        }
        
        print(f"Résultats pour {nom_region}:")
        print(f"Surface installée: {surface_panneau_region:.2f} m²")
        print(f"Puissance installée: {puissance_installee_kw:.2f} kW")
        print(f"Production annuelle: {production['energie_annuelle_wh']/1000:,.2f} kWh")
    
    return resultats_regions

def calcul_couts_solarpowerplant(energie_centrales):
    """
    Calcule le coût total pour chaque centrale solaire basé sur leur production annuelle.
    
    Parameters
    ----------
    energie_wh : pandas.Series
        Production d'énergie annuelle en Wh pour chaque emplacement.
    
    Returns
    -------
    float
        Coûts en dollars
    """
    # Calcul de la puissance crête
    heures_equivalent_pleine_puissance = 1200
    puissance_crete_w = energie_centrales/ heures_equivalent_pleine_puissance
    puissance_crete_kw = puissance_crete_w / 1000
    puissance_crete_mw = puissance_crete_kw / 1000
    
    # Coût de référence par MW (40M$ / 9.5MW)
    cout_par_mw = 40000000 / 9.5
    couts = puissance_crete_mw * cout_par_mw
    
    # Ne retourner que les coûts
    return couts

def calcul_emissions_co2(energie_centrales):
    """
    Calcule les émissions de CO2 équivalent pour chaque centrale solaire.
    
    Parameters
    ----------
    energie_wh : pandas.Series
        Production d'énergie annuelle en Wh pour chaque emplacement.
    
    Returns
    -------
    pandas.Series
        Émissions de CO2 en kg pour chaque emplacement.
    """
    # Convertir Wh en kWh
    energie_kwh = energie_centrales / 1000
    
    # Facteur d'émission en g CO2eq/kWh
    facteur_emission = 64
    emissions_g = energie_kwh * facteur_emission
    emissions_kg = emissions_g / 1000
    
    return emissions_kg

coordinates_residential = [
    (48.4808, -68.5210, 'Bas-Saint-Laurent', 0, 'Etc/GMT+5'),
    (48.4284, -71.0683, 'Saguenay–Lac-Saint-Jean', 0, 'Etc/GMT+5'),
    (46.8139, -71.2082, 'Capitale-Nationale', 0, 'Etc/GMT+5'),
    (46.3420, -72.5477, 'Mauricie', 0, 'Etc/GMT+5'),
    (45.4036, -71.8826, 'Estrie', 0, 'Etc/GMT+5'),
    (45.5017, -73.5673, 'Montréal', 0, 'Etc/GMT+5'),
    (45.4215, -75.6919, 'Outaouais', 0, 'Etc/GMT+5'),
    (48.0703, -77.7600, 'Abitibi-Témiscamingue', 0, 'Etc/GMT+5'),
    (50.0340, -66.9141, 'Côte-Nord', 0, 'Etc/GMT+5'),
    (53.4667, -76.0000, 'Nord-du-Québec', 0, 'Etc/GMT+5'),
    (48.8360, -64.4931, 'Gaspésie–Îles-de-la-Madeleine', 0, 'Etc/GMT+5'),
    (46.5000, -70.9000, 'Chaudière-Appalaches', 0, 'Etc/GMT+5'),
    (45.6066, -73.7124, 'Laval', 0, 'Etc/GMT+5'),
    (46.0270, -73.4360, 'Lanaudière', 0, 'Etc/GMT+5'),
    (45.9990, -74.1428, 'Laurentides', 0, 'Etc/GMT+5'),
    (45.4500, -73.3496, 'Montérégie', 0, 'Etc/GMT+5'),
    (46.4043, -72.0169, 'Centre-du-Québec', 0, 'Etc/GMT+5'),
]
coordinates_centrales = [
    (45.4167, -73.4999, 'La Prairie', 0, 'Etc/GMT+5'),
    (45.6833, -73.4333, 'Varennes', 0, 'Etc/GMT+5'),
]

population_relative = {
    "Bas-Saint-Laurent": 0.0226,
    "Saguenay-Lac-Saint-Jean": 0.0317,
    "Capitale-Nationale": 0.0897,
    "Mauricie": 0.0318,
    "Estrie": 0.0580,
    "Montréal": 0.2430,
    "Outaouais": 0.0472,
    "Abitibi-Témiscamingue": 0.0165,
    "Côte-Nord": 0.0099,
    "Nord-du-Québec": 0.0052,
    "Gaspésie-Îles-de-la-Madeleine": 0.0102,
    "Chaudière-Appalaches": 0.0503,
    "Laval": 0.0508,
    "Lanaudière": 0.0620,
    "Laurentides": 0.0744,
    "Montérégie": 0.1675,
    "Centre-du-Québec": 0.0291
}

Cout_centrales = calcul_couts_solarpowerplant(energie_centrales)
CO2_centrales = calcul_emissions_co2(energie_centrales)

end_time = time.time()

print(f"Les coûts pour les centrales solaires sont de {Cout_centrales:,.2f} $")
print(f"Le CO2 pour les centrales solaires est de {CO2_centrales:,.2f} kg")
print(f"\nTemps d'exécution : {end_time - start_time:.2f} secondes")



# Exemple d'utilisation
if __name__ == "__main__":
    # Test avec une surface de 100 m²
    surface_test = 100  # m²
    
    print("\nDébut des calculs pour toutes les régions du Québec...")
    resultats = calculate_regional_residential_solar(
        coordinates_residential,
        surface_test,
        surface_tilt=0,
        surface_orientation=180
    )
    
    # Affichage du résumé des résultats
    print("\n=== RÉSUMÉ DES RÉSULTATS POUR TOUTES LES RÉGIONS ===")
    energie_totale = 0
    for nom_region, data in resultats.items():
        energie_totale += data['energie_annuelle_kwh']
        print(f"\n{nom_region}:")
        print(f"  Production annuelle : {data['energie_annuelle_kwh']:,.2f} kWh")
        print(f"  Surface installée : {data['surface_installee_m2']:.2f} m²")
        print(f"  Puissance installée : {data['puissance_installee_kw']:.2f} kW")
    
    print(f"\nProduction totale pour toutes les régions : {energie_totale:,.2f} kWh")
    
    end_time = time.time()
    print(f"\nTemps d'exécution : {end_time - start_time:.2f} secondes")
import pvlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def get_weather_data(coordinates):
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
    for location in coordinates:
        latitude, longitude, name, altitude, timezone = location
        print(f"\nRécupération des données météo pour {name}...")
        weather = pvlib.iotools.get_pvgis_tmy(latitude, longitude)[0]
        weather.index.name = "utc_time"
        tmys.append(weather)
    return tmys

def calculate_solar_parameters(weather, latitude, longitude, altitude, temperature_model_parameters, module, inverter, surface_tilt, surface_azimuth):
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
        surface_azimuth,
        solpos["apparent_zenith"],
        solpos["azimuth"],
    )
    total_irradiance = pvlib.irradiance.get_total_irradiance(
        surface_tilt,
        surface_azimuth,
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

def solar_energy_production(coordinates, show_plot=False):
    """
    Calcule l'énergie solaire annuelle pour les emplacements spécifiés.

    Parameters
    ----------
    coordinates : list of tuples
        Liste des coordonnées des emplacements sous forme de tuples (latitude, longitude, nom, altitude, fuseau horaire).
    show_plot : bool, optional
        Si True, affiche le graphique de production d'énergie. Par défaut False.

    Returns
    -------
    Series
        Énergies annuelles (Wh) pour chaque emplacement.
    """
    print("\nInitialisation des modèles solaires...")
    sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')

    module = sandia_modules['Canadian_Solar_CS5P_220M___2009_']
    inverter = sapm_inverters['ABB__MICRO_0_25_I_OUTD_US_208__208V_']
    temperature_model_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']

    print("\nRécupération des données météorologiques...")
    tmys = get_weather_data(coordinates)
    energies = {}

    print("\nCalcul de la production solaire...")
    for location, weather in zip(coordinates, tmys):
        latitude, longitude, name, altitude, timezone = location
        ac = calculate_solar_parameters(weather, latitude, longitude, altitude, temperature_model_parameters, module, inverter, 30, 180)
        annual_energy = ac.sum()
        energies[name] = annual_energy

    energies = pd.Series(energies)
    print("Énergies annuelles (Wh) :")
    print(energies.apply(lambda x: f"{x:.2f} Wh"))

    if show_plot:
        energies.plot(kind='bar', rot=0)
        plt.ylabel('Yearly energy yield (Wh)')
        plt.title('Yearly Energy Yield of Solar Plants')
        plt.show()

    return energies

def residential_solar_energy_production(coordinates, show_plot=False):
    """
    Calcule l'énergie solaire annuelle pour les emplacements spécifiés avec des panneaux résidentiels.

    Parameters
    ----------
    coordinates : list of tuples
        Liste des coordonnées des emplacements sous forme de tuples (latitude, longitude, nom, altitude, fuseau horaire).
    show_plot : bool, optional
        Si True, affiche le graphique de production d'énergie. Par défaut False.

    Returns
    -------
    Series
        Énergies annuelles (Wh) pour chaque emplacement.
    """
    print("\nInitialisation des modèles solaires...")
    sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')

    module = sandia_modules['Canadian_Solar_CS5P_220M___2009_']
    inverter = sapm_inverters['ABB__MICRO_0_25_I_OUTD_US_208__208V_']
    temperature_model_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']

    print("\nRécupération des données météorologiques...")
    tmys = get_weather_data(coordinates)
    energies = {}

    print("\nCalcul de la production solaire...")
    for location, weather in zip(coordinates, tmys):
        latitude, longitude, name, altitude, timezone = location
        print(f"Calcul pour {name}...")
        ac = calculate_solar_parameters(weather, latitude, longitude, altitude, temperature_model_parameters, module, inverter, 30, 180)
        annual_energy = ac.sum()
        energies[name] = annual_energy
        print(f"Calcul terminé pour {name}")

    energies = pd.Series(energies)
    print("Énergies annuelle TMY (Wh) :")
    print(energies.apply(lambda x: f"{x:.2f}"))

    if show_plot:
        energies.plot(kind='bar', rot=0)
        plt.ylabel('Yearly energy yield (Wh)')
        plt.title('Yearly Energy Yield of Solar Plants')
        plt.show()

    return energies

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


def calcul_couts_solarpowerplant(energie_wh):
    """
    Calcule le coût total pour chaque centrale solaire basé sur leur production annuelle.
    
    Parameters
    ----------
    energie_wh : pandas.Series
        Production d'énergie annuelle en Wh pour chaque emplacement.
    
    Returns
    -------
    tuple
        (puissance_crete_kw, couts) : puissance crête en kW et coûts en dollars
    """
    # Calcul de la puissance crête
    heures_equivalent_pleine_puissance = 1200
    puissance_crete_w = energie_wh / heures_equivalent_pleine_puissance
    puissance_crete_kw = puissance_crete_w / 1000
    puissance_crete_mw = puissance_crete_kw / 1000
    
    # Coût de référence par MW (40M$ / 9.5MW)
    cout_par_mw = 40000000 / 9.5
    couts = puissance_crete_mw * cout_par_mw
    
    return puissance_crete_kw, couts

def calcul_emissions_co2(energie_wh):
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
    energie_kwh = energie_wh / 1000
    
    # Facteur d'émission en g CO2eq/kWh
    facteur_emission = 64
    emissions_g = energie_kwh * facteur_emission
    emissions_kg = emissions_g / 1000
    
    return emissions_kg

def calcul_resultats_complets():
    """
    Calcule et affiche tous les résultats pour chaque centrale solaire :
    - Production d'énergie
    - Puissance crête
    - Coûts d'installation
    - Émissions de CO2
    """
    # Obtenir la production d'énergie
    energie_wh = solar_energy_production(coordinates, show_plot=False)
    
    # Calculer les coûts et la puissance crête
    puissance_crete_kw, couts = calcul_couts_solarpowerplant(energie_wh)
    
    # Calculer les émissions de CO2
    emissions_kg = calcul_emissions_co2(energie_wh)
    
    print("\n=== RÉSULTATS PAR EMPLACEMENT ===")
    
    # Affichage des résultats pour chaque emplacement
    for emplacement in energie_wh.index:
        print(f"\n--- {emplacement} ---")
        print(f"Production annuelle : {energie_wh[emplacement] / 1000:,.2f} kWh")
        print(f"Puissance crête : {puissance_crete_kw[emplacement]:.2f} kW")
        print(f"Coût d'installation estimé : {couts[emplacement]:,.2f} $")
        print(f"Émissions CO2 : {emissions_kg[emplacement]:.2f} kg CO2eq/an")
    
    return {
        'energie_kwh': energie_wh / 1000,
        'puissance_kw': puissance_crete_kw,
        'couts': couts,
        'emissions': emissions_kg
    }

# Coordinates for the locations of the solar plants
coordinates = [
    (45.5017, -73.5673, 'Montréal', 0, 'Etc/GMT+5'),
    (45.4167, -73.4999, 'La Prairie', 0, 'Etc/GMT+5'),
    (45.6833, -73.4333, 'Varennes', 0, 'Etc/GMT+5'),
]

# Exécution des calculs
print("\nCalcul de la production d'énergie, des coûts et des émissions :")
resultats = calcul_resultats_complets()

print("\n=== RÉSULTATS GLOBAUX ===")
print(resultats)

def calculate_energy_from_power(coordinates, puissance_kw, surface_tilt=30, surface_azimuth=180):
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
    surface_azimuth : float, optional
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
    latitude, longitude, name, altitude, timezone = coordinates
    
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
        surface_tilt, surface_azimuth
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

# Exemple d'utilisation
if __name__ == "__main__":
    # Exemple de coordonnées (Montréal)
    coord_test = (45.6833, -73.4333, 'Varennes', 0, 'Etc/GMT+5')
    
    puissance_test = 9500  # 100 kW
    
    resultats = calculate_energy_from_power(coord_test, puissance_test)
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
        print(f"Données récupérées pour {name}")
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
        ac = calculate_solar_parameters(weather, latitude, longitude, altitude, temperature_model_parameters, module, inverter)
        annual_energy = ac.sum()
        energies[name] = annual_energy
        print(f"Calcul terminé pour {name}")

    energies = pd.Series(energies)
    print("Énergies annuelles (Wh) :")
    print(energies.apply(lambda x: f"{x:.2f} Wh"))

    if show_plot:
        energies.plot(kind='bar', rot=0)
        plt.ylabel('Yearly energy yield (Wh)')
        plt.title('Yearly Energy Yield of Solar Plants')
        plt.show()

    return energies

def residential_solar_energy_production(coordinates):
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
        ac = calculate_solar_parameters(weather, latitude, longitude, altitude, temperature_model_parameters, module, inverter)
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

# Coordinates for the locations of the solar plants
plants_coordinates = [
    (45.5017, -73.5673, 'Montréal', 0, 'Etc/GMT+5'),
    (45.4167, -73.4999, 'La Prairie', 0, 'Etc/GMT+5'),
    (45.6833, -73.4333, 'Varennes', 0, 'Etc/GMT+5'),
]
"""
Liste des coordonnées des emplacements des centrales solaires.

Chaque tuple contient les informations suivantes :
- Latitude : float
    Latitude de l'emplacement en degrés.
- Longitude : float
    Longitude de l'emplacement en degrés.
- Nom : str
    Nom de l'emplacement.
- Altitude : float
    Altitude de l'emplacement en mètres.
- Fuseau horaire : str
    Fuseau horaire de l'emplacement.

Exemples
--------
(45.5017, -73.5673, 'Montréal', 36, 'Etc/GMT+5')
(45.4167, -73.4999, 'La Prairie', 20, 'Etc/GMT+5')
(45.6833, -73.4333, 'Varennes', 20, 'Etc/GMT+5')
"""
# Appel des fonctions
#solar_energy_production(coordinates)

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
    puissance_crete_kw = puissance_crete_w / 1_000
    puissance_crete_mw = puissance_crete_kw / 1_000
    
    # Coût de référence par MW (40M$ / 9.5MW)
    cout_par_mw = 40_000_000 / 9.5
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
    tuple
        (energie_kwh, emissions_kg) : énergie en kWh et émissions en kg CO2eq
    """
    # Convertir Wh en kWh
    energie_kwh = energie_wh / 1000
    
    # Facteur d'émission en g CO2eq/kWh
    facteur_emission = 64
    emissions_g = energie_kwh * facteur_emission
    emissions_kg = emissions_g / 1000
    
    return energie_kwh, emissions_kg

def calcul_resultats_complets():
    """
    Calcule et affiche tous les résultats pour chaque centrale solaire :
    - Production d'énergie
    - Puissance crête
    - Coûts d'installation
    - Émissions de CO2
    """
    # Obtenir la production d'énergie
    energie_wh = solar_energy_production(plants_coordinates, show_plot=False)
    
    # Calculer les coûts et la puissance crête
    puissance_crete_kw, couts = calcul_couts_solarpowerplant(energie_wh)
    
    # Calculer les émissions et obtenir l'énergie en kWh
    energie_kwh, emissions_kg = calcul_emissions_co2(energie_wh)
    
    print("\n=== RÉSULTATS PAR EMPLACEMENT ===")
    
    # Affichage des résultats pour chaque emplacement
    for emplacement in energie_wh.index:
        print(f"\n--- {emplacement} ---")
        print(f"Production annuelle : {energie_kwh[emplacement]:,.2f} kWh")
        print(f"Puissance crête : {puissance_crete_kw[emplacement]:.2f} kW")
        print(f"Coût d'installation estimé : {couts[emplacement]:,.2f} $")
        print(f"Émissions CO2 : {emissions_kg[emplacement]:.2f} kg CO2eq/an")
    
    return {
        'energie_kwh': energie_kwh,
        'puissance_kw': puissance_crete_kw,
        'couts': couts,
        'emissions': emissions_kg
    }

# Exécution des calculs
print("\nCalcul de la production d'énergie, des coûts et des émissions :")
resultats = calcul_resultats_complets()




    
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

def solar_energy_production(coordinates):
    """
    Calcule l'énergie solaire annuelle pour les emplacements spécifiés.

    Parameters
    ----------
    coordinates : list of tuples
        Liste des coordonnées des emplacements sous forme de tuples (latitude, longitude, nom, altitude, fuseau horaire).

    Returns
    -------
    Series
        Énergies annuelles (Wh) pour chaque emplacement.
    """
    sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')

    module = sandia_modules['Canadian_Solar_CS5P_220M___2009_']
    inverter = sapm_inverters['ABB__MICRO_0_25_I_OUTD_US_208__208V_']
    temperature_model_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']

    tmys = get_weather_data(coordinates)
    energies = {}

    for location, weather in zip(coordinates, tmys):
        latitude, longitude, name, altitude, timezone = location
        # Utilisez des valeurs optimisées pour l'angle et l'orientation des panneaux
        surface_tilt = 50  # inclinaison favorisant la production hivernale
        surface_azimuth = 180  # Orientation plein sud
        ac = calculate_solar_parameters(weather, latitude, longitude, altitude, temperature_model_parameters, module, inverter, surface_tilt, surface_azimuth)
        annual_energy = ac.sum()
        energies[name] = annual_energy

    energies = pd.Series(energies)
    print("Énergies annuelles (Wh) :")
    print(energies.apply(lambda x: f"{x:.2f} Wh"))

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

    Returns
    -------
    Series
        Énergies annuelles (Wh) pour chaque emplacement.
    """
    sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')

    module = sandia_modules['Canadian_Solar_CS5P_220M___2009_']
    inverter = sapm_inverters['ABB__MICRO_0_25_I_OUTD_US_208__208V_']
    temperature_model_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']

    tmys = get_weather_data(coordinates)
    energies = {}

    for location, weather in zip(coordinates, tmys):
        latitude, longitude, name, altitude, timezone = location
        # Utilisez des valeurs fixes pour l'angle et l'orientation des panneaux résidentiels
        surface_tilt = 0  # Angle des panneaux fixé à 0°
        surface_azimuth = 180  # Orientation plein sud
        ac = calculate_solar_parameters(weather, latitude, longitude, altitude, temperature_model_parameters, module, inverter, surface_tilt, surface_azimuth)
        annual_energy = ac.sum()
        energies[name] = annual_energy

    energies = pd.Series(energies)
    print("Énergies annuelles résidentielles par MRC (Wh) :")
    print(energies.apply(lambda x: f"{x:.2f} Wh"))

    energies.plot(kind='bar', rot=45)
    plt.ylabel('Yearly residential energy yield (Wh)')
    plt.title('Yearly Residential Energy Yield per MRC')
    plt.show()

    return energies

# Coordinates for the locations of the solar plants
plants_coordinates = [
    (45.5017, -73.5673, 'Montréal', 0, 'Etc/GMT+5'),
    (45.4167, -73.4999, 'La Prairie', 0, 'Etc/GMT+5'),
    (45.6833, -73.4333, 'Varennes', 0, 'Etc/GMT+5'),
]

MRC_coordinates = [
    (46.8139, -71.2082, 'Capitale-Nationale', 0, 'Etc/GMT+5'),  
    (45.5017, -73.5673, 'Montréal', 0, 'Etc/GMT+5'),  
    (45.7640, -74.0059, 'Laurentides', 0, 'Etc/GMT+5'), 
    (46.3430, -72.5477, 'Mauricie', 0, 'Etc/GMT+5'),  
    (45.5534, -73.5529, 'Laval', 0, 'Etc/GMT+5'),  
    (45.5019, -73.5674, 'Montérégie', 0, 'Etc/GMT+5'),  
    (46.8299, -71.2540, 'Chaudière-Appalaches', 0, 'Etc/GMT+5'), 
    (46.8033, -71.2428, 'Saguenay-Lac-Saint-Jean', 0, 'Etc/GMT+5'), 
    (48.4284, -71.0594, 'Côte-Nord', 0, 'Etc/GMT+5'),  
    (45.4042, -71.8824, 'Estrie', 0, 'Etc/GMT+5'),  
]
# Appel des fonctions pour la production des centrales solaires
# solar_energy_production(plants_coordinates)

# Appel des fonctions pour la production résidentielle
residential_solar_energy_production(MRC_coordinates)
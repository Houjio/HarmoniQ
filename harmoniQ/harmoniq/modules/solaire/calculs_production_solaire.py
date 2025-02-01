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

def calculate_solar_parameters(weather, latitude, longitude, altitude, temperature_model_parameters, module, inverter):
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
        Altitude de l'emplacement.
    temperature_model_parameters : dict
        Paramètres du modèle de température.
    module : dict
        Paramètres du module solaire.
    inverter : dict
        Paramètres de l'onduleur.

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
        latitude,
        180,
        solpos["apparent_zenith"],
        solpos["azimuth"],
    )
    total_irradiance = pvlib.irradiance.get_total_irradiance(
        latitude,
        180,
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
        ac = calculate_solar_parameters(weather, latitude, longitude, altitude, temperature_model_parameters, module, inverter)
        annual_energy = ac.sum()
        energies[name] = annual_energy

    energies = pd.Series(energies)
    print("Énergies annuelle TMY (Wh) :")
    print(energies.apply(lambda x: f"{x:.2f}"))

    energies.plot(kind='bar', rot=0)
    plt.ylabel('Yearly energy yield (Wh)')
    plt.title('Yearly Energy Yield of Solar Plants')
    plt.show()

    return energies

# Coordinates for the locations of the solar plants
coordinates = [
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
    Altitude de l'emplacement en mètres. fixé à 0 pour simplification.
- Fuseau horaire : str
    Fuseau horaire de l'emplacement.

Exemples
--------
(45.5017, -73.5673, 'Montréal', 0, 'Etc/GMT+5')
(45.4167, -73.4999, 'La Prairie', 0, 'Etc/GMT+5')
(45.6833, -73.4333, 'Varennes', 0, 'Etc/GMT+5')
"""
# Appel des fonctions
solar_energy_production(coordinates)
from harmoniq.db.engine import * 
from harmoniq.db.shemas import *
from harmoniq.core.meteo import WeatherHelper, Granularity, Type
import pandas as pd

db = next(get_db())

def get_parcs_name():
    """
    Cette fonction permet de récupérer les noms des parcs éoliens
    dans la base de données.
    """    
    # Appel des parcs de la base de données
    parcs = read_eolienne_parcs(db)

    # Récupération des noms des parcs
    parcs_name = [parc.nom for parc in parcs]
    return parcs_name

def get_parc_id(parc_name):
    """
    Cette fonction permet de récupérer l'identifiant d'un parc éolien
    dans la base de données.
    """
    # Appel des parcs de la base de données
    parcs = read_eolienne_parcs(db)

    # Récupération de l'identifiant du parc
    for parc in parcs:
        if parc.nom == parc_name:
            parc_id = parc.id
    return parc_id

def get_eolienne_parcs_weather_data(start_time, end_time, granularity, parc_name):
    """
    Cette fonction permet de récupérer les données météorologiques pour chaque éolienne
    dans la base de données. Elle utilise la classe WeatherHelper du module harmoniq.core.meteo.
    
    La fonction prend comme input les paramètres suivants:
    
    - start_time: datetime, date de début de la simulation, format (année, mois, jour);
    - end_time: datetime, date de fin de la simulation, format (année, mois, jour);
    - granularity: Granularity, granularité des données météorologiques, (HOURLY ou DAILY);
    - type: Type, type de l'infrastructure (NONE, HYDRO, SOLAIRE, EOLIEN).
    
    """
    # Identifications du parc_id
    parc_id = get_parc_id(parc_name)
    
    # Appel des parcs de la base de données
    parc = read_eolienne_parc(db, parc_id)
    
    # Appel des données météorologiques pour chaque éolienne
    position = PositionBase(latitude=parc.latitude, longitude=parc.longitude)
    weather = WeatherHelper(
        position, True, start_time, end_time, Type.EOLIEN, granularity
    )
    data = weather.load()
    
    if granularity == Granularity.DAILY:
        weather_data = pd.DataFrame({
            "wind_speed": data[data["Spd of Max Gust (km/h)"].notna()],
            "wind_direction": data[data["Dir of Max Gust (10s deg)"].notna()],
            "temperature": data[data["Mean Temp (°C)"].notna()],
        })
    elif granularity == Granularity.HOURLY:
        weather_data = pd.DataFrame({
            "wind_speed": data[data["Wind Spd (km/h)"].notna()],
            "wind_direction": data[data["Wind Dir (10s deg)"].notna()],
            "temperature": data[data["Temp (°C)"].notna()],
            "pressure": (1/1000)*data[data["Stn Press (kPa)"].notna()], # Pa
        })
    return data

# Exemple d'utilisation de la fonction get_eolienne_weather_data
start_time = datetime(2020, 1, 1)
end_time = datetime(2021, 1, 1)
granularity = Granularity.DAILY

a = get_eolienne_parcs_weather_data(start_time, end_time, granularity, "Carleton")

a = a[a['Spd of Max Gust (km/h)'].notna()]
print(a['Spd of Max Gust (km/h)'])
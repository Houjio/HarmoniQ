from harmoniq.modules.eolienne.eolienne_db import db
from harmoniq.db.engine import * 
from harmoniq.db.shemas import *
from harmoniq.core.meteo import WeatherHelper, Granularity, Type

def get_eolienne_weather_data(start_time, end_time, granularity, type):
    """
    Cette fonction permet de récupérer les données météorologiques pour chaque éolienne
    dans la base de données. Elle utilise la classe WeatherHelper du module harmoniq.core.meteo.
    
    La fonction prend comme input les paramètres suivants:
    
    - start_time: datetime, date de début de la simulation, format (année, mois, jour);
    - end_time: datetime, date de fin de la simulation, format (année, mois, jour);
    - granularity: Granularity, granularité des données météorologiques, (HOURLY ou DAILY);
    - type: Type, type de l'infrastructure (NONE, HYDRO, SOLAIRE, EOLIEN).
    
    """    
    # Appel des éoliennes de la base de données
    eoliennes = read_eoliennes(db)

    # Appel des données météorologiques pour chaque éolienne
    for eolienne in eoliennes:
        if eolienne.eolienne_parc_id == 1:
            position = PositionBase(latitude=eolienne.latitude, longitude=eolienne.longitude)
            weather = WeatherHelper(position, True, start_time, end_time, granularity, type)
            data = weather.load()
        else:
            continue
    return data

# Exemple d'utilisation de la fonction get_eolienne_weather_data
start_time = datetime(2020, 1, 1)
end_time = datetime(2021, 1, 2)
granularity = 2
type = Type.EOLIEN

station = get_eolienne_weather_data(start_time, end_time, granularity, type)
print(station)
import requests
from datetime import datetime
import pandas as pd

from enum import Enum


def fetch_historical_weather(
    iata_id: int, date_debut: datetime, date_fin: datetime
) -> dict:
    """
    Récupère les données météo historiques pour une station météo donnée.

    Args:
        iata_id (int): L'identifiant IATA de la station météo.
        date_debut (datetime): La date de début de la période de données météo à récupérer.
        date_fin (datetime): La date de fin de la période de données météo à récupérer.

    Returns:
        dict: Les données météo historiques pour la station météo donnée.
    """
    url = f"https://dd.weather.gc.ca/observations/swob-ml/{iata_id}/"
    params = {
        "start": date_debut.strftime("%Y%m%d"),
        "end": date_fin.strftime("%Y%m%d"),
    }

    params = {
        "start": (datetime.now() - pd.Timedelta(days=2)).strftime("%Y%m%d"),
        "end": (datetime.now() - pd.Timedelta(days=1)).strftime("%Y%m%d"),
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

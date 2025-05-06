Guide E : Météo Data Processing Guide
===========================

Ce guide décrit simplement comment HarmoniQ récupère des données de l'API Open-Meteo.

Étapes
------

Récupération des données via l'API Open-Meteo (pour les curieux)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Accédez à la documentation de l'API Open-Meteo :

   https://open-meteo.com/en/docs/historical-weather-api


2. Effectuez une requête HTTP GET pour récupérer les données au format JSON.

   Exemple de requête avec `curl` :

   .. code-block:: bash

      curl -X GET "https://api.open-meteo.com/v1/history?latitude=45.5017&longitude=-73.5673&start_date=2010-01-01&end_date=2020-12-31&temperature_unit=celsius" -H "accept: application/json"

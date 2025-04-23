Guide E : Météo Data Processing Guide
===========================

Ce guide décrit pas à pas comment obtenir et traiter les données météorologiques
pour le projet HarmoniQ.

Étapes
------

Téléchargement des données
~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Accédez à la page des données climatiques horaires de SNRC:

   https://climate-change.canada.ca/climate-data/#/hourly-climate-data

2. Sélectionnez la période et les stations souhaitées.
3. Cliquez sur **Télécharger** pour obtenir les fichiers CSV.

Placement des fichiers
~~~~~~~~~~~~~~~~~~~~~~

Copiez les fichiers CSV téléchargés **tels quels** dans :

.. code-block:: bash

   cd /path/to/HarmoniQ/harmoniq/core/meteo
   mkdir -p raw
   cp ~/Downloads/*.csv raw/


Lancement du script de traitement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Depuis le répertoire racine du projet :

.. code-block:: bash

   cd /path/to/HarmoniQ
   python3 core/meteo/meteo_data_refiner.py


Le script va :

- Lire et concaténer tous les CSV du dossier `core/meteo/raw/`.
- Nettoyer et formater les données.
- Générer `meteo_data.csv` dans `core/meteo/refined/`.

Vérification du résultat
~~~~~~~~~~~~~~~~~~~~~~~~

Ouvrez `core/meteo/refined/meteo_data.csv` et vérifiez :

- L'ordre des colonnes.
- La présence de la colonne `ORIGINAL_DATA`.

Utilisation dans le code
~~~~~~~~~~~~~~~~~~~~~~~~

Exemple d'intégration de `WeatherHelper` :

```python
from harmoniq.core.meteo import WeatherHelper, Granularity, EnergyType
from harmoniq.db.schemas import PositionBase
from datetime import datetime
import asyncio

pos = PositionBase(latitude=45.80944, longitude=-73.43472)
weather = WeatherHelper(
    position=pos,
    interpolate=False,
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 2),
    data_type=EnergyType.EOLIEN,
    granularity=Granularity.HOURLY
)
df = asyncio.run(weather.load())
print(df.head())
```

Vous pouvez maintenant exploiter les données météo dans HarmoniQ !
```

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
   - Pour la période, choisissez **2010-2020**.
   - Pour les stations, sélectionnez uniquement des stations QC, les autres provinces ont des structures de données différentes.

   ![Sélection des données](images/selection.png)
3. Cliquez sur **Télécharger** pour obtenir les fichiers CSV.

Placement des fichiers
~~~~~~~~~~~~~~~~~~~~~~

Copiez les fichiers CSV téléchargés **tels quels** dans :

.. code-block:: bash

    HarmoniQ/harmoniQ/harmoniq/meteo/raw


Lancement du script de traitement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Depuis le répertoire racine du projet (ayant le bon environement activé) :

.. code-block:: bash

   cd /path/to/harmoniq --> A remplacer par le bon chemin
   python3 meteo/meteo_data_refiner.py


Le script va :

- Lire et concaténer tous les CSV du dossier `core/meteo/raw/`.
- Nettoyer et formater les données.
- Générer `meteo_data.csv` dans `core/meteo/refined/`.

Vérification du résultat
~~~~~~~~~~~~~~~~~~~~~~~~

Ouvrez `core/meteo/refined/meteo_data.csv` et vérifiez :

- L'ordre des colonnes.
- La présence de la colonne `ORIGINAL_DATA`.

A savoir: ces données .CSV seront utilisées à l'execution de meteo.py dans HarmoniQ/harmoniQ/harmoniq/core/meteo.py

Il est possible de tester meteo.py seul en le lancant directement depuis un terminal avec le bon environement activé :

.. code-block:: bash

    cd /path/to/harmoniq --> A remplacer par le bon chemin
    python3 core/meteo.py
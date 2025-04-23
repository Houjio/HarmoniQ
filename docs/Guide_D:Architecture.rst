Partie D : Structure du projet
==============================

Vue d’ensemble du dépôt HarmoniQ :

.. code-block:: text

   HARMONIQ/                    <- racine du dépôt
   ├─ docs/                     <- fichiers de documentation statique
   ├─ harmoniQ/                 <- package Python principal
   │  ├─ harmoniq/              <- code applicatif central
   │  │  ├─ __init__.py
   │  │  ├─ _version.py
   │  │  ├─ core/               <- services partagés et décorateurs (base.py, meteo.py, etc.)
   │  │  ├─ db/                 <- modèles SQLAlchemy, schémas Pydantic, CRUD, moteur, BDs de test
   │  │  ├─ météo/                 <- regulation et formattage des données météo (à effectuer une seule fois lorsque l'on change de donées)
   │  │  ├─ modules/            <- un sous‑package par type d’énergie (éolien, solaire, hydro, etc.)
   │  │  ├─ scripts/            <- scripts utilitaires (init_database, launch_webserver, load_database)
   │  │  └─ webserver/           <- routeurs FastAPI & endpoints REST
   │  ├─ __init__.py
   │  └─ _version.py
   ├─ tests/                    <- tests unitaires et d’intégration
   ├─ pyproject.toml            <- métadonnées du projet et dépendances
   ├─ README.md                 <- vue d’ensemble du projet et instructions
   └─ harmoniq_env/             <- environnement virtuel Python


.. note::

   Le dépôt est organisé en plusieurs sous‑répertoires, chacun ayant un rôle spécifique dans le projet.
   Le code applicatif principal est contenu dans le répertoire ``harmoniQ/harmoniq/``.
   Les tests unitaires et d’intégration sont situés dans le répertoire ``tests/``.
   Les fichiers de documentation statique se trouvent dans le répertoire ``docs/``.

.. note::

   Les modules de production énérgetique sont appelés dans le fichier REST.py du repertoire ``webserver/``.
   
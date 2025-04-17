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
   │  │  ├─ modules/            <- un sous‑package par type d’énergie (éolien, solaire, hydro, etc.)
   │  │  ├─ scripts/            <- scripts utilitaires (init_database, launch_webserver, load_database)
   │  │  └─ webserver/           <- routeurs FastAPI & endpoints REST
   │  ├─ __init__.py
   │  └─ _version.py
   ├─ tests/                    <- tests unitaires et d’intégration
   ├─ pyproject.toml            <- métadonnées du projet et dépendances
   ├─ README.md                 <- vue d’ensemble du projet et instructions
   └─ harmoniq_env/             <- environnement virtuel Python
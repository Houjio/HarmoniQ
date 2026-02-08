==========================================
Guide B : Environnement et installation
==========================================

Choisissez une méthode d'installation.

Méthode recommandée : script tout-en-un
----------------------------------------

À la racine du projet (répertoire contenant ``harmoniQ/``) :

.. code-block:: bash

    chmod +x exec_harmoniQ.sh
    ./exec_harmoniQ.sh

Le script crée un venv dans ``.venv/`` à la racine du projet (s'il n'existe pas), installe HarmoniQ, initialise la base et lance l'app sur un port libre. Détails : :doc:`app`.

Méthode A : Conda
-----------------

1. Créer l'environnement ::

    conda create --name harmoniq_env python=3.10

2. Activer ::

    conda activate harmoniq_env

3. Depuis la racine du projet ::

    pip install -e ./harmoniQ[dev]

Méthode B : venv (Linux / macOS)
---------------------------------

1. Créer l'environnement ::

    python3 -m venv harmoniq_env

2. Activer ::

    source harmoniq_env/bin/activate

3. Installer ::

    pip install -U pip
    pip install -e ./harmoniQ[dev]

Méthode C : venv (Windows)
--------------------------

1. Créer l'environnement ::

    python -m venv harmoniq_env

2. Activer ::

    .\harmoniq_env\Scripts\activate

3. Installer ::

    pip install -e ./harmoniQ[dev]

Initialisation de la base
-------------------------

Après la première installation ::

    init-db -p

Pour réinitialiser complètement puis remplir ::

    init-db -R -p

Données de demande (demande.db ou synthèse)
-------------------------------------------

Au lancement avec le script, vous pouvez choisir :

- ``./exec_harmoniQ.sh --demande-db`` : utiliser la base **demande.db** (fichier requis dans ``harmoniQ/harmoniq/db/``).
- ``./exec_harmoniQ.sh --demande-synthetic`` : utiliser la **synthèse** (courbe en canard + saisonnalité), pas de fichier.

Sans option, le script utilise la base si ``demande.db`` existe, sinon la synthèse. Pour obtenir ``demande.db`` (accès réservé) : ``load-db -d`` ou copie manuelle dans ``harmoniQ/harmoniq/db/``.

Lancer l'application
--------------------

.. code-block:: bash

    launch-app --debug --port 5000

En cas d'erreur « Address already in use », utiliser un autre port (ex. ``--port 5001``) ou lancer via ``./exec_harmoniQ.sh``, qui choisit automatiquement un port libre.

Voir :doc:`app` pour toutes les options.

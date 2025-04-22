==========================================
Partie B : Environnement et Lancement
==========================================
Choisissez une méthode pour créer un environnement Python.

Méthode A : Conda
^^^^^^^^^^^^^^^^^

1. Créez l'environnement Conda :

.. code-block:: bash

    conda create --name harmoniq_env python=3.8

2. Activez-le :

.. code-block:: bash

    conda activate harmoniq_env

3. Installez les dépendances :

.. code-block:: bash

    pip install -e ./harmoniQ[dev]

Méthode B : Virtualenv
^^^^^^^^^^^^^^^^^^^^^^

1. Créez un environnement virtuel (ou vous voulez):

.. code-block:: bash

    python -m venv harmoniq_env

2. Activez-le :

- **Linux/MacOS :**

.. code-block:: bash

    source harmoniq_env/bin/activate

- **Windows :**

.. code-block:: bash

    .\harmoniq_env\Scripts\activate

3. Installez les dépendances :

.. code-block:: bash

    pip install -e ./harmoniQ[dev]

Et si la commande précédente ne fonctionne pas, essayez :
.. code-block:: bash

    pip install -e ./harmoniQ

N'oubliez pas d'updaer pip

Vérification du Fichier ``demande.db``
--------------------------------------

Assurez-vous que le fichier suivant existe et est accessible :

HarmoniQ/harmoniQ/harmoniq/db/

Lancer l’Application
--------------------

Pour initialiser la base de données :

.. code-block:: bash

    init-db -p

Télécharger les données nécessaires (réservé aux étudiants du projet) :

.. code-block:: bash

    load-db -d

Lancer l'application web (mode debug) :

.. code-block:: bash

    launch-app --debug

Si aucun problème ne survient, HarmoniQ est prêt à être utilisé ! Si une erreur survient indiquant:

.. code-block:: bash

    [Errno 48] Address already in use

Alors il faut simplement changer le port dans : harmoniq/scripts/lance_webserver.py

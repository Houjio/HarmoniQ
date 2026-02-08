===================================================
Guide A : Prérequis et configuration
===================================================

Ce guide décrit les prérequis système et la pré-configuration pour HarmoniQ.

Cloner le projet
----------------

.. code-block:: bash

    git clone https://github.com/Houjio/HarmoniQ.git
    cd HarmoniQ

Prérequis
---------

- **Python 3.8 à 3.12** (3.10 ou 3.12 recommandé). Python 3.14 n'est pas supporté (dépendances comme numpy 1.26.4).
- **pip** à jour

Sous macOS avec Homebrew : ``brew install python@3.12`` ; le script ``exec_harmoniQ.sh`` utilisera ``python3.12`` automatiquement.

macOS (Homebrew)
^^^^^^^^^^^^^^^^

Pour installer les bibliothèques système optionnelles (proj, pyproj) :

.. code-block:: bash

    brew install proj
    brew install pyproj

L'environnement virtuel peut être créé avec le script de lancement (voir :doc:`install` et :doc:`app`) ou manuellement avec ``python3 -m venv`` / conda.

Suite
-----

- **Installation et environnement** : :doc:`Guide_B:Installation`
- **Lancer l'application** : :doc:`app`

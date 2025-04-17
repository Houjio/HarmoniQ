===================================================
Guide de Lancement et Notes de Projet pour HarmoniQ
===================================================


======================================
Partie A : Guide de l'Application
======================================

Pré-Configuration de HarmoniQ
-----------------------------

Ce guide contient les étapes nécessaires pour installer et lancer HarmoniQ.

Cloner le Projet depuis GitHub
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Clonez le dépôt officiel depuis GitHub (préférablement sur le bureau) :

.. code-block:: bash

    git clone https://github.com/Houjio/HarmoniQ.git

Placez-vous dans le répertoire cloné :

.. code-block:: bash

    cd HarmoniQ

Pré-requis pour macOS (Homebrew)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Homebrew permet une gestion simplifiée des packages requis.

Installer Homebrew
~~~~~~~~~~~~~~~~~~
Exécutez dans un terminal :

.. code-block:: bash

    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

Ajouter Homebrew au PATH
~~~~~~~~~~~~~~~~~~~~~~~~
Après installation :

.. code-block:: bash

    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> /Users/mon_user/.zprofile
    eval "$(/opt/homebrew/bin/brew shellenv)"

Vérifier l'installation
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    brew -v

Installer les bibliothèques système
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    brew install proj
    brew install pyproj
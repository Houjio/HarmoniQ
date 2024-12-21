############
Installation
############

Pour installer le projet, il faut créer un nouvelle environnement python et installer les dépendances. Ce tutoriel propose une installation avec conda et une autre avec Virtualenv.

Installation avec conda
-----------------------

1. Créer un environnement conda avec python 3.8
::
    conda create --name harmoniq_env python=3.8

2. Activer l'environnement
::
    conda activate harmoniq_env

3. Installer les dépendances
::
    pip install -e -r requirements.txt
    
Installation avec Virtualenv
----------------------------

1. Créer un environnement virtuel
::
    python -m venv harmoniq_env

2. Activer l'environnement
Linux/MacOS
::
    source harmoniq_env/bin/activate

Windows
::
    .\harmoniq_env\Scripts\activate

3. Installer les dépendances
4. ::
    pip install -e -r requirements.txt



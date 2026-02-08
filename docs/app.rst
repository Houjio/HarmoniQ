####################
Lancer l'application
####################

Prérequis : environnement activé et dépendances installées (voir :doc:`install`).

Lancement avec le script (recommandé)
======================================

À la racine du projet ::

    ./exec_harmoniQ.sh

Le script :

- Crée ou active l'environnement Python (utilise pyenv si disponible)
- Installe HarmoniQ si nécessaire
- Initialise la base avec ``init-db -p``
- Choisit un **port libre** (défaut 5000, puis 5001, 5002… si occupé)
- Lance l'app en mode debug

Ouvrir l'URL affichée (ex. http://127.0.0.1:5000). En cas de conflit de port avec pyenv ou un autre outil, le script bascule automatiquement sur le port suivant.

Lancement manuel
================

1. Initialiser la base (une fois) ::

    init-db -p

   Pour tout réinitialiser puis remplir ::

    init-db -R -p

2. Lancer le serveur ::

    launch-app --debug --port 5000

   Ou en production (plusieurs workers) ::

    launch-app --host 0.0.0.0 --port 5000

Options de ``launch-app``
=========================

- ``--debug`` : rechargement à la volée (développement)
- ``--host 0.0.0.0`` : écoute sur toutes les interfaces (défaut)
- ``--port 5000`` : port HTTP (défaut 5000)

Erreur « Address already in use »
=================================

Si le port par défaut est occupé, utiliser un autre port ::

    launch-app --debug --port 5001

Ou lancer via ``./exec_harmoniQ.sh``, qui choisit automatiquement un port libre.

Données de demande (demande.db ou synthèse)
============================================

Deux modes possibles :

- **Base réelle** (fichier ``demande.db``) : avec le script ::

    ./exec_harmoniQ.sh --demande-db

  Le fichier doit se trouver dans ``harmoniQ/harmoniq/db/demande.db`` (ou le télécharger via ``load-db -d``).

- **Synthèse** (courbe en canard + saisonnalité, aucun fichier) ::

    ./exec_harmoniQ.sh --demande-synthetic

Sans option, le script utilise la base si ``demande.db`` existe, sinon la synthèse.

En lancement manuel, utiliser la variable d'environnement ::

    HARMONIQ_DEMANDE_MODE=db launch-app --debug
    # ou
    HARMONIQ_DEMANDE_MODE=synthetic launch-app --debug

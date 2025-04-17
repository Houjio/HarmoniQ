Partie C : Guide de Débogage pour l'Application Web HarmoniQ
============================================================

Ce document fournit des étapes de dépannage, des commandes et des informations utiles pour déboguer l'application web HarmoniQ.

Gestion de l'erreur "Address already in use"
--------------------------------------------

Si vous rencontrez l'erreur suivante lors du démarrage de l'application :

    [Errno 48] Address already in use

Cela signifie que le port que vous essayez d'utiliser est déjà occupé par un autre processus. Pour résoudre ce problème, vous devez redémarrer l'application avec un port différent.

Solution
~~~~~~~~
Pour démarrer l'application sur un nouveau port, utilisez la commande suivante :

.. code-block:: bash

    launch-app --debug --port ####

Remplacez `####` par le numéro de port souhaité (par exemple, 5001, 5002, etc.).
Vous pouvez également vérifier quel processus utilise le port avec la commande suivante :

.. code-block:: bash

    lsof -i :<port_number>

Informations sur FastAPI sur le site web
----------------------------------------

Après avoir lancé l'application, vous pouvez accéder à la documentation FastAPI et interagir manuellement avec l'API. C'est un outil précieux pour déboguer et exécuter des méthodes spécifiques.

Pour accéder à la documentation FastAPI, visitez l'URL suivante :

.. code-block:: bash

    http://0.0.0.0:####/docs

Remplacez `####` par le numéro de port que vous avez utilisé pour lancer l'application (par exemple, 5000, 5001, etc.).

Cette interface FastAPI vous permet de :
- Voir tous les points de terminaison disponibles et leurs paramètres
- Exécuter manuellement des méthodes et inspecter les réponses
- Tester des appels API spécifiques directement depuis l'interface du navigateur

Méthodes d'aide en ligne de commande
------------------------------------

Si vous avez besoin de plus d'informations sur l'utilisation de commandes spécifiques, voici quelques méthodes d'aide utiles en ligne de commande.

Initialisation de la base de données (`init-db`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pour initialiser la base de données ou effectuer des opérations telles que la réinitialisation, le remplissage ou la population, vous pouvez utiliser la commande `init-db`.

Pour voir l'aide de la commande `init-db`, exécutez :

.. code-block:: bash

    init-db -h

Cela affichera les options d'utilisation suivantes :

.. code-block:: bash

    usage: init-db [-h] [-t] [-R] [-f] [-p]

    Initialise la base de données

    options:
      -h, --help     Affiche ce message d'aide et quitte
      -t, --test     Utilise la base de données de test
      -R, --reset    Réinitialise la base de données
      -f, --fill     Remplit la base de données si elle est vide
      -p, --populate Remplit la base de données avec des données de référence

Exemple
~~~~~~~
Pour initialiser la base de données avec des données de test, utilisez :

.. code-block:: bash

    init-db -t

Cela configurera la base de données avec des données de test prédéfinies.

Lancement de l'application (`launch-app`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pour démarrer l'application web HarmoniQ, utilisez la commande `launch-app`. Vous pouvez également spécifier des options comme `--debug`, `--host` et `--port` pour personnaliser le processus de démarrage.

Pour afficher le message d'aide pour la commande `launch-app`, exécutez :

.. code-block:: bash

    launch-app -h

Cela affichera les options d'utilisation suivantes :

.. code-block:: bash

    usage: launch-app [-h] [--debug] [--host HOST] [--port PORT]

    Lancer l'interface web

    options:
      -h, --help     Affiche ce message d'aide et quitte
      --debug        Active le mode débogage
      --host HOST    Adresse IP du serveur
      --port PORT    Port du serveur

Exemple
~~~~~~~
Pour lancer l'application en mode débogage sur le port 5001, utilisez :

.. code-block:: bash

    launch-app --debug --port 5001

Cela démarrera l'application avec le mode débogage activé, vous permettant de voir des messages d'erreur détaillés et des journaux dans la console.

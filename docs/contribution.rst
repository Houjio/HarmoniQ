############
Contribution
############

Pour ajouter des fonctionnalités aux projets, il faut ajouter des fonctions dans les modules Python dont vous êtes responsable. La liste des modules sont les suivants :

- harmoniQ/harmoniq/modules/eolienne
- harmoniQ/harmoniq/modules/hydro
- harmoniQ/harmoniq/modules/solaire
- harmoniQ/harmoniq/modules/stockage
- harmoniQ/harmoniq/modules/thermique
- harmoniQ/harmoniq/modules/transmission

Des fichiers peuvent être ajoutés dans les dossiers pour ajouter de nouvelle fonctions et classes, tans qu'elle sont aussi importer dans le fichier __init__.py du dossier. 

Du code souvant réutilisé dans plusieurs modules peut être mis dans le dossier harmoniQ/harmoniq/utils. Pour l'importer dans les autres modules, il suffit d'ajouter la ligne suivante au début du fichier :

.. code-block:: python

    from harmoniq.utils import NOM_DE_LA_FONCTION

Pour ajouter des tests, il faut ajouter des tests dans le dossier harmoniQ/tests. Les tests doivent être écrits avec le module unittest de Python. Pour lancer les tests, il suffit de lancer la commande suivante :

.. code-block:: bash

    python -m unittest discover -s tests

############
Contribution
############

Pour ajouter des fonctionnalités, ajoutez du code dans les modules Python concernés.

Modules de production
----------------------

- ``harmoniQ/harmoniq/modules/eolienne``
- ``harmoniQ/harmoniq/modules/hydro``
- ``harmoniQ/harmoniq/modules/solaire``
- ``harmoniQ/harmoniq/modules/thermique``
- ``harmoniQ/harmoniq/modules/nucleaire``
- ``harmoniQ/harmoniq/modules/reseau`` (réseau électrique)
- ``harmoniQ/harmoniq/modules/transmission``

Nouvelles fonctions et classes : les ajouter dans le module concerné et les exposer dans le ``__init__.py`` du dossier.

Code partagé
------------

Le code réutilisé par plusieurs modules peut être placé dans :

- ``harmoniQ/harmoniq/core/`` (utils, base, meteo)
- ``harmoniQ/harmoniq/modules/reseau/utils/`` pour le réseau

Exemple d'import ::

    from harmoniq.core.utils import NOM_DE_LA_FONCTION

Tests
-----

Les tests vont dans ``harmoniQ/tests/``. Utiliser **pytest**. Lancer tous les tests ::

    cd harmoniQ
    pytest

Les tests utilisent une base dédiée (variable d'environnement ``HARMONIQ_TESTING=True``).

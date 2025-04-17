.. code-block:: rst
   :linenos:

    Uniformisation des modules d'énergie
    ====================================

    Objectif
    --------
    Unifier les entrées et sorties de tous les modules d'énergie (éolien, solaire, hydro, nucléaire, thermique, stockage, réseau), afin de garantir une interface cohérente et faciliter l'évolution et l'intégration.

    1. Schéma d'entrée
    ------------------
    Le schéma d'entrée décrit les données nécessaires à chaque module pour instancier une infrastructure et charger un scénario.

    **Caractéristiques communes :**
    - **id** (int) : Identifiant unique de l'infrastructure.
    - **nom** (str) : Nom de l'infrastructure.
    - **latitude**, **longitude** (float) : Coordonnées géographiques.
    - **capacite** (float) : Capacité installée (en MW ou unité adaptée).
    - **params** (Dict[str, Any]) : Paramètres spécifiques au module (par défaut `{}`).
    - **scenario** (ScenarioInput) : Scénario météo/demande, défini par :
      - **nom** (str) : Nom du scénario.
      - **debut**, **fin** (datetime) : Dates de début et de fin.
      - **granularite** (Granularity) : Granularité temporelle.
      - **data** (List[Dict[str, Any]]) : Liste de points temporels, chaque dict contenant `dateTime` et les variables associées (vent, irradiance, débits, demande, etc.).

    .. code-block:: python

       from pydantic import BaseModel
       from typing import List, Dict, Any
       from datetime import datetime
       from harmoniq.core.meteo import Granularity

       class InfrastructureInput(BaseModel):
           id: int
           nom: str
           latitude: float
           longitude: float
           capacite: float
           params: Dict[str, Any] = {}

       class ScenarioInput(BaseModel):
           nom: str
           debut: datetime
           fin: datetime
           granularite: Granularity
           data: List[Dict[str, Any]]

    2. Schéma de sortie
    -------------------
    Le schéma de sortie renvoie pour chaque module d'énergie les indicateurs clés suivants :

    - **production_ts** (List[Dict[str, Any]]) : Série temporelle de production, chaque dict `{dateTime: datetime, production: float}`.
    - **production_totale** (float) : Production totale sur la période (MWh ou unité adaptée).
    - **facteur_charge** (float) : Facteur de charge moyen.
    - **cout_total** (float) : Coût total (monnaie locale).
    - **emission_co2** (float) : Émissions de CO₂ (kg ou tonnes).

    .. code-block:: python

       class EnergyModuleOutput(BaseModel):
           production_ts: List[Dict[str, Any]]
           production_totale: float
           facteur_charge: float
           cout_total: float
           emission_co2: float

    3. Documentation étape par étape
    --------------------------------
    - Créer les schémas `InfrastructureInput`, `ScenarioInput` et `EnergyModuleOutput` dans `harmoniq/db/schemas/common.py`.
    - Mettre à jour la classe `Infrastructure` (dans `harmoniq/core/base.py`) pour :
      - Accepter un `InfrastructureInput` et un `ScenarioInput` en entrée.
      - Retourner un `EnergyModuleOutput` en sortie.
    - Modifier chaque module (`eolienne`, `solaire`, `hydro`, etc.) pour :
      - Refactorer le constructeur (`__init__`) et la méthode de calcul (`calculer_production` ou équivalent).
      - Utiliser les nouveaux schémas en entrée et en sortie.
    - Adapter les endpoints FastAPI (`harmoniq/webserver/REST.py`) pour renvoyer `EnergyModuleOutput`.
    - Mettre à jour et ajouter des tests unitaires dans `tests/` pour valider la nouvelle interface.

    4. Mise en œuvre détaillée
    --------------------------
    Pour chaque module :

    1. **Refactoring entrée** : remplacer les arguments individuels par un seul `InfrastructureInput`.
    2. **Refactoring scénario** : remplacer l'appel `charger_scenario(scenario)` par l'utilisation de `ScenarioInput`.
    3. **Refactoring sortie** : dans la méthode de calcul, construire et retourner un `EnergyModuleOutput`.
    4. **Tests** : écrire des tests qui valident la conformité des entrées et sorties.

    .. note::
       Après chaque étape, exécuter la suite de tests avec `pytest` pour s'assurer que rien n'est cassé.


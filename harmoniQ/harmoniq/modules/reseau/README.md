# Module Réseau - HarmoniQ

## Introduction

Le module Réseau modélise et optimise le système électrique. Il permet de:

- Construire et analyser un réseau électrique complet basé sur PyPSA
- Optimiser la production d'électricité en minimisant les coûts
- Gérer les réservoirs hydrauliques 
- Analyser les flux de puissance
- Calculer la capacité optimale d'import/export d'électricité

## Point d'Entrée et Flux de Travail

Le point d'entrée principal est la classe `InfraReseau` dans `__init__.py`. Cette classe implémente le workflow complet:

```python
from harmoniq.modules.reseau import InfraReseau
from harmoniq.db.schemas import ListeInfrastructures, ScenarioBase

# Initialiser avec une liste d'infrastructures
infra_reseau = InfraReseau(liste_infrastructures)

# Charger un scénario
infra_reseau.charger_scenario(scenario)

# Exécuter le workflow complet
network, statistics = await infra_reseau.workflow_import_export(liste_infrastructures, is_journalier=True)

# Calculer la production par type d'énergie
production = await infra_reseau.calculer_production(liste_infrastructures, is_journalier=True)
```

## Fonctionnalités Principales

### 1. Création du Réseau (`creer_reseau`)
- Utilise `NetworkBuilder` pour construire un réseau PyPSA
- Charge les données statiques (buses, lignes, générateurs)
- Charge les données temporelles (demande, disponibilité des sources)
- Utilise un cache pour éviter de reconstruire le réseau à chaque exécution

### 2. Calcul de la Capacité d'Import/Export (`calculer_capacite_import_export`)
- Détermine la capacité optimale d'import/export pour équilibrer le système

### 3. Optimisation des Réservoirs (`fake_optimiser_reservoirs`)
- Modélise la gestion des réservoirs hydrauliques
- Calcule des coûts marginaux dynamiques basés sur les niveaux des réservoirs
- Optimise la production avec `NetworkOptimizer`

### 4. Analyse de Production (`calculer_production`)
- Calcule la production par type d'énergie (hydraulique, éolienne, solaire, etc.)
- Convertit les puissances (MW) en énergies (MWh)
- Fournit des statistiques sur la production

## Interaction avec les Autres Modules

Le module Réseau interagit avec plusieurs autres composants d'HarmoniQ:

1. **Module Hydro**
   - Utilise la fonction `reservoir_infill` pour calculer les niveaux de réservoir
   - Charge les données d'apport naturel des barrages

2. **Module Éolien**
   - Récupère les données de production éolienne
   - Incorpore les profils de génération dans le réseau

3. **Module Solaire**
   - Intègre les données de production solaire
   - Utilise les profils de génération dans l'optimisation

4. **Module Thermique**
   - Inclut les centrales thermiques dans l'optimisation

5. **Base de Données**
   - Utilise le module `harmoniq.db.CRUD` pour lire les données d'infrastructure
   - Charge les scénarios et paramètres depuis la base de données

## Fichiers Clés et leurs Fonctionnalités

### Core

- **`network_builder.py`**: Orchestre la construction du réseau et l'analyse des résultats
  - `create_network()`: Crée un réseau PyPSA complet
  - `optimize_network()`: Optimise la production du réseau
  - `run_power_flow()`: Exécute un calcul de flux de puissance

- **`optimization.py`**: Contient les algorithmes d'optimisation
  - `optimize_manually()`: Optimise la production selon les priorités et coûts
  - `check_optimization_feasibility()`: Vérifie si le problème est faisable

- **`power_flow.py`**: Calcule les flux de puissance dans le réseau
  - `run_power_flow()`: Exécute un calcul de flux (AC ou DC)
  - `get_line_loading()`: Calcule le chargement des lignes
  - `analyze_network_losses()`: Calcule les pertes dans le réseau

### Utils

- **`energy_utils.py`**: Fonctions pour les calculs énergétiques
  - `calcul_cout_reservoir()`: Calcule le coût marginal d'un réservoir
  - `ensure_network_solvability()`: Corrige les problèmes de connectivité
  - `reechantillonner_reseau_journalier()`: Convertit un réseau horaire en journalier

- **`data_loader.py`**: Charge les données pour le réseau
  - `load_network_data()`: Charge les données statiques du réseau
  - `load_timeseries_data()`: Charge les séries temporelles
  - `load_demand_data()`: Charge les données de demande énergétique

## Limites Actuelles

1. **Gestion des Réservoirs**: La méthode `fake_optimiser_reservoirs` utilise des niveaux de réservoir simulés, pas encore basés sur une véritable optimisation hydraulique avec `reservoir_infill`

2. **Flux de Puissance**: Le calcul des flux de puissance complet n'est pas encore intégré au workflow principal

3. **Connectivité du Réseau**: La fonction `ensure_network_solvability` est une solution temporaire pour garantir la connectivité, mais pas optimale

4. **Génération d'Urgence**: Le système ajoute des générateurs d'urgence (importations) en cas de déficit, ce qui devrait être géré de manière plus rigoureuse

5. **Répartition de la Charge**: La charge est distribuée de manière semi-aléatoire entre les nœuds, une approche plus réaliste est nécessaire

## TODOs et Développements Futurs

1. **Amélioration de l'Optimisation**:
   ```python
   # TODO: Remplacer par un appel à l'optimiseur PyPSA standard n.optimize()
   ```
   - Remplacer l'optimiseur manuel par l'optimiseur de PyPSA standard

2. **Intégration du Power Flow**:
   ```python
   # TODO : Ajouter le calcul du power flow (DC ou AC) (Du NetworkBuilder ou du PowerFlowAnalyzer)
   ```
   - Intégrer un calcul complet du flux de puissance au workflow

3. **Gestion des Réservoirs**:
   - Implémenter la gestion dynamique réelle des niveaux des réservoirs
   - La méthode `optimiser_avec_gestion_reservoirs` doit remplacer `fake_optimiser_reservoirs`

4. **Topologie du Réseau**:
   - Améliorer la connectivité du réseau pour éviter les lignes virtuelles
   - Développer une meilleure solution pour les composants isolés

5. **Interconnexions**:
   - Améliorer la modélisation des interconnexions avec les réseaux voisins

6. **Visualisations**:
   - Développer des visualisations plus avancées pour l'analyse des résultats
   - Le module `visualization_utils.py` doit être étendu

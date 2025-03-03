# Architecture du Module Réseau

Ce document explique l'architecture et l'organisation du module reseau (network). Il servira de guide pour comprendre la structure du modèle et savoir où trouver les différentes fonctionnalités.

## Vue d'ensemble

Le projet est organisé en plusieurs modules principaux :

```
network/
├── core/           # Fonctionnalités principales du réseau
├── utils/          # Utilitaires et outils de support
├── tests/          # Tests unitaires et d'intégration
├── data/           # Données du réseau
├── main_core.py    # Script principal pour les fonctionnalités core
└── main_utils.py   # Script principal pour les utilitaires
```

## 🎯 Modules Principaux

### 1. Core (`/core`)

Ce module contient les fonctionnalités essentielles du réseau électrique.

#### Fichiers principaux :

- **network_builder.py** : Point d'entrée principal pour créer et configurer le réseau
  - `NetworkBuilder` : Classe principale pour construire le réseau
  - Utilisez ce fichier pour créer un nouveau réseau ou modifier sa configuration

- **optimization.py** : Gestion de l'optimisation du réseau
  - `NetworkOptimizer` : Optimise la production électrique
  - Calcule la répartition optimale de la production

- **power_flow.py** : Calculs des flux de puissance
  - `PowerFlowAnalyzer` : Analyse les flux dans le réseau
  - Permet de faire des calculs AC et DC

### 2. Utils (`/utils`)

Ce module contient les outils de support et utilitaires.

#### Fichiers principaux :

- **data_loader.py** : Chargement des données
  - `NetworkDataLoader` : Charge les données depuis les fichiers CSV
  - Utilisez ce fichier pour modifier la façon dont les données sont chargées

- **geo_utils.py** : Utilitaires géographiques
  - `GeoUtils` : Calculs de distances et optimisation des tracés
  - Utile pour les analyses géographiques du réseau

- **time_utils.py** : Gestion des séries temporelles
  - `TimeSeriesManager` : Analyse des données temporelles
  - Analyse des pics de demande et statistiques saisonnières

- **visualization_utils.py** : Outils de visualisation
  - `NetworkVisualizer` : Création de visualisations du réseau
  - Génération de graphiques et cartes

- **lines_filter.py** : Filtrage des lignes
  - `LineFilter` : Filtrage et géolocalisation des lignes
  - Utilisé pour la préparation des données de lignes

- **validators.py** : Validation des données
  - `NetworkValidator` : Vérifie la cohérence des données
  - Assure la qualité des données du réseau

### 3. Tests (`/tests`)

Contient les tests unitaires et d'intégration.

- **test_network_builder.py** : Tests de la construction du réseau
- **test_power_flow.py** : Tests des calculs de flux

## 📊 Organisation des Données (`/data`)

Les données sont organisées comme suit :

```
data/
├── regions/
│   └── buses.csv         # Points de connexion du réseau
│
├── topology/
│   ├── lines/
│   │   ├── line_types.csv    # Types de lignes standard
│   │   └── lines.csv         # Lignes de transmission
│   │
│   ├── centrales/
│   │    ├── carriers.csv      # Types de production
│   │    ├── generators_non_pilotable.csv  # Centrales non pilotables
│   │    └── generators_pilotable.csv      # Centrales pilotables
│   │
│   └── constraints/
│        └── global_constraints.csv  # Contraintes globales
│
└── timeseries/
    └── 2024/
        ├── generation/
        │   ├── generators-p_max_pu.csv       # Production max non pilotable
        │   └── generators-marginal_cost.csv   # Coûts marginaux pilotables
        └── loads-p_set.csv                    # Profils de charge
```

## 🚀 Comment Utiliser le Modèle

Le modèle peut être utilisé via deux scripts principaux situés à la racine du projet :

### 1. main_core.py - Fonctionnalités Principales

Ce script permet de tester les fonctionnalités fondamentales du réseau :

```python
from network import NetworkCoreManager

# Création du gestionnaire
manager = NetworkCoreManager()

# Test de création du réseau
success_creation = manager.test_network_creation()
if not success_creation:
    print("Échec de la création du réseau")
    
# Test des calculs de flux
success_pf = manager.test_power_flow()
if not success_pf:
    print("Échec des calculs de flux")
    
# Test de l'optimisation
success_opt = manager.test_optimization()
if not success_opt:
    print("Échec de l'optimisation")
    
# Test de l'analyse complète
success_analysis = manager.test_complete_analysis()
if not success_analysis:
    print("Échec de l'analyse complète")
```

Ce script vous permet de :
- Créer et configurer le réseau
- Visualiser les détails des bus, lignes et générateurs
- Effectuer des calculs de flux de puissance (AC/DC)
- Optimiser la production
- Réaliser une analyse complète du réseau

### 2. main_utils.py - Utilitaires et Analyses

Ce script permet de tester les fonctionnalités utilitaires :

```python
from network import NetworUtilskManager

# Création du gestionnaire
manager = NetworUtilskManager()

# Chargement et validation des données
success_load = manager.load_and_validate()
if success_load:
    manager.print_network_info()

# Test des visualisations
success_viz = manager.test_visualizations()

# Test des analyses temporelles
success_time = manager.test_time_analysis()

# Test des calculs géographiques
success_geo = manager.test_geo_calculations()
```

Ce script vous permet de :
- Charger et valider les données du réseau
- Créer des visualisations du réseau
- Analyser les séries temporelles
- Effectuer des calculs géographiques
- Gérer les données des lignes de transmission


## 📚 Ressources Additionnelles

- Installation : Voir `INSTALL.md` pour les instructions d'installation
- Dépendances : Voir `requirements.txt` pour la liste des packages requis

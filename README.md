# HarmoniQ

Outil de modélisation de la production d'énergie au Québec (éolien, solaire, hydro, thermique, nucléaire, réseau).

## Installation

Voir le guide : [Installation](docs/install.rst).

## Lancer le projet

**Option 1 – Script tout-en-un (recommandé)**  
À la racine du projet :

```bash
./exec_harmoniQ.sh
```

Le script crée ou active l'environnement Python, installe HarmoniQ, initialise la base, choisit un port libre (défaut 5000) et lance l'app. Ouvrir `http://127.0.0.1:<port>`.

**Option 2 – À la main**  
Dans un environnement virtuel (après `pip install -e ./harmoniQ[dev]` et `init-db -p`) :

```bash
launch-app --debug --port 5000
```

Pour plus d'informations, voir la [documentation de lancement](docs/app.rst).

### Données de demande (demande)

Deux modes au choix :

- **Base réelle** (projet initial) : fichier `harmoniQ/harmoniq/db/demande.db`. Avec le script : `./exec_harmoniQ.sh --demande-db`.
- **Synthèse** : courbe en canard + profil saisonnier (aucun fichier). Avec le script : `./exec_harmoniQ.sh --demande-synthetic`.

Sans option, le script utilise la base si `demande.db` existe, sinon la synthèse. En lancement manuel : `HARMONIQ_DEMANDE_MODE=db` ou `=synthetic` (ex. `HARMONIQ_DEMANDE_MODE=synthetic launch-app --debug`).

## Contribution

Voir le guide [Contribution](docs/contribution.rst).

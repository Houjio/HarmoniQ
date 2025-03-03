# Guide d'Installation

Ce guide vous accompagnera pas à pas dans l'installation de l'environnement de développement pour le module réseau.

## Prérequis

- Python 3.9 ou supérieur
- pip (gestionnaire de paquets Python)
- git (pour cloner le dépôt)

## 1. Vérification de Python

Ouvrez un terminal et vérifiez votre version de Python :

```bash
python --version
```

Si Python n'est pas installé, téléchargez-le sur [python.org](https://www.python.org/downloads/).

## 2. Création de l'environnement virtuel

Un environnement virtuel permet d'isoler les dépendances du projet. Voici comment le créer :

### Sous Windows
```bash
# Naviguez vers le dossier du projet
cd /chemin/vers/network

# Créez l'environnement virtuel
python -m venv venv

# Activez l'environnement virtuel
venv\Scripts\activate
```

### Sous Linux/Mac
```bash
# Naviguez vers le dossier du projet
cd /chemin/vers/network

# Créez l'environnement virtuel
python -m venv venv

# Activez l'environnement virtuel
source venv/bin/activate
```

💡 **Note**: Votre terminal devrait maintenant afficher `(venv)` au début de la ligne, indiquant que l'environnement virtuel est actif.

## 3. Installation des dépendances

Une fois l'environnement virtuel activé :

```bash
# Mise à jour de pip
python -m pip install --upgrade pip

# Installation des dépendances
pip install -r requirements.txt
```

⚠️ **Important**: L'installation peut prendre quelques minutes, c'est normal !

## 4. Vérification de l'installation

Pour vérifier que tout est bien installé :

```bash
python -c "import pypsa; print(pypsa.__version__)"
```

Si aucune erreur n'apparaît et qu'une version s'affiche, l'installation est réussie ! 🎉

## Problèmes courants et solutions

### "Python n'est pas reconnu..."
➡️ Vérifiez que Python est bien ajouté à votre PATH système.

### Erreurs lors de l'installation des packages
➡️ Essayez d'installer les packages un par un pour identifier celui qui pose problème :
```bash
pip install pypsa
pip install pandas
# etc...
```

### L'environnement virtuel ne s'active pas
➡️ Vérifiez que vous êtes dans le bon dossier et que l'environnement a bien été créé.

## Pour quitter l'environnement virtuel

Quand vous avez fini de travailler :
```bash
deactivate
```

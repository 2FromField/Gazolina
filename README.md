# Gazolina

Projet visant à récupérer les prix annoncés des stations esssences sur différents carburants dans une zone géographique. Associée avec une application streamlit (dashboard) facilitant la prise de décision journalière et l'historique des fluctuations.

## BPMN

-> A FAIRE

## Source(s) de données

- MonEssence.fr : https://mon-essence.fr/ville/29383-mauregny-en-haye?q=02820

# Base de données

## Schéma

-> draw.io A FAIRE

## Type de données

-> Tables (nom colonne, description, type, valeurs)

# Architecture du projet

-> Treefile à faire

# Services indexés

## Airflow

### Pré-requis

1. Installer les dépendances:

```
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv build-essential \
                        libpq-dev postgresql postgresql-contrib
```

## UV

### Installation

1. Installation des UV pour Linux : `curl -LsSf https://astral.sh/uv/install.sh | sudo sh`
2. Ajouter UV dans le $PATH : `source $HOME/.local/bin/env`
3. Vérifier l'installation : `uv --version`

### Notes utiles

1. Créer et nommer le projet : `uv init $UV_PROJECT_NAME`
2. Naviguer dans le projet : `cd $UV_PROJECT_NAME`
3. Utiliser UV : `uv add $PACKAGE`

| Commade                           |                                         Description |
| --------------------------------- | --------------------------------------------------: |
| `uv add $PACKAGE`                 |                Ajouter une ou plusieurs dépendances |
| `uv add $PACKAGE=2.0.2`           |    Ajouter une dépendance sous une certaine version |
| `uv remove $PACKAGE`              |                            Supprimer une dépendance |
| `uv python list --only-installed` | Afficher la liste des dépendances et leurs versions |
| `uv run $PYTHON_FILENAME.py`      |                 Exécuter des scripts python avec UV |
| `uv export -o requirements.txt`   |                 Générer le fichier requirements.txt |

# Configuration de la VM GCP

## Création

- Région: europe-west1 (Belgique)
- Zone: europe-west1-b
- Type: e2-medium (2 vCPU, 1 coeur(s), 4 Go de mémoire)

## Connexion depuis VSCode

1. Vérifier l'identifiant du compte GCP: `gcloud auth list`

- Si l'adresse mail n'est pas celle du compte, l'ajouter: `gcloud auth login` et suivre les indication de la page web

2. Vérifier que l'on cible le bon projet contenant notre VM: `gcloud config get-value project` (l'identifiant se trouve sur GCP lors du choix du projet)

- Si ce n'est pas le bon projet, redéfinir la target: `gcloud config set project $PROJECT_ID`

3. Vérifier que la vm est bien présente dans le projet:

```
gcloud compute instances list --project $PROJECT_ID \
  --filter='name=("$VM_NAME")' \
  --format='table(project, name, zone, status, networkInterfaces[].accessConfigs[].natIP)'
```

4. S'y connecter:

```
gcloud compute ssh $VM_NAME \
  --project $PROJECT_ID \
  --zone $VM_ZONE \
  -- -vvv
```

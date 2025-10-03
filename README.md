# Gazolina

## BPMN

-> A FAIRE

## Liens des pages web:

- MonEssence.fr : https://mon-essence.fr/ville/29383-mauregny-en-haye?q=02820
- Carburant.org : https://www.carburants.org/prix-carburants/aisne.02/aizelles.kwTwwC/

# Base de données

## Schéma

-> draw.io A FAIRE

## Type de données

-> Tables (nom colonne, description, type, valeurs)

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

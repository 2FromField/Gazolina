# Gazolina

![Kubernetes](https://img.shields.io/badge/Kubernetes-v10.2-3069DE?style=for-the-badge&logo=kubernetes&logoColor=white)
![ArgoCD](https://img.shields.io/badge/Argo%20CD-v10.2-1e0b3e?style=for-the-badge&logo=argo&logoColor=#d16044)
![Airflow](https://img.shields.io/badge/Airflow-v10.2-017CEE?style=for-the-badge&logo=Apache%20Airflow&logoColor=white)
![Python](https://img.shields.io/badge/Python-v10.2-FFD43B?style=for-the-badge&logo=python&logoColor=blue)
![GCP](https://img.shields.io/badge/Google_Cloud-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white)

Projet visant à récupérer les prix annoncés des stations esssences sur différents carburants dans une zone géographique. Associé à une application streamlit (dashboard) facilitant la prise de décision journalière et affichant l'historique des fluctuations.

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

- Installer k8s:

```
sudo apt-get update
sudo apt-get install -y ca-certificates curl apt-transport-https gnupg
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key \
  | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' \
  | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update && sudo apt-get install -y kubectl
kubectl version --client
```

- Installer helm:

```
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
```

- Installer un driver Docker:

```
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# Repository Docker officiel
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
| sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# démarrer et activer
sudo systemctl enable --now docker

# Activer le sudo mode
sudo usermod -aG docker $USER
newgrp docker
docker info
```

- Cluster local minikube (sans GKE)

```
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Lancer minikube avec le driver docker
minikube start --driver=docker

# Vérifier les noeuds et pods
kubectl get nodes
kubectl -n kube-system get pods
```

### Services installés

#### ArgoCD

- Créer le namespace & installer le manifest

```
kubectl create namespace argocd
kubectl -n argocd apply -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

- Accéder à l'UI par port-forward: `kubectl -n argocd port-forward svc/argocd-server 8080:443`

- Créer un tunnel pour accéder à l'UI sur votre ordinateur (sur le terminal du PC):

```
gcloud auth login # s'authentifier
gcloud config set project gazolina # setup le projet

# Ouvrir le tunnel
gcloud compute ssh vm-gazolina \
  --project gazolina --zone europe-west1-b \
  -- -N -L 8443:127.0.0.1:8080
```

- S'authentifier avec l'utilisateur "admin" et le password créé: `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo`

#### Airflow

- Préparer l'accès Git pour la git-sync (via SSH):

```
# Génère une clé SANS passphrase (ou réutilise ta deploy-key GitHub)
ssh-keygen -t ed25519 -N "" -f ./id_ed25519 -C "airflow@cluster"
cat ./id_ed25519.pub

# known_hosts GitHub (ed25519) :
ssh-keyscan github.com > ./known_hosts
```

- Créer le namespace pour Airflow: `kubectl create namespace airflow`

- Créer un secret dans le namespace pour la clé SSH:

```
kubectl -n airflow create secret generic airflow-ssh-secret \
  --from-file=gitSshKey=./id_ed25519 \
  --from-file=known_hosts=./known_hosts
```

- Appliquer le fichier yaml: `kubectl apply -f https://raw.githubusercontent.com/2FromField/Gazolina/main/uv_gazolina/helm/airflow-app.yaml`

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

OU </br>

```
gcloud compute instances create vm-gazolina \
  --project gazolina \
  --zone europe-west1-b \
  --machine-type=e2-medium \
  --image-family=debian-12 \
  --image-project=debian-cloud
```

## Supprimer

Supprimer l'instance et son disque boot, puis recréer une VM neuve: </br>

```
gcloud compute instances delete vm-gazolina \
  --project gazolina \
  --zone europe-west1-b \
  --delete-disks=all
```

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

4. Installation des composants GCP cloud: `gcloud components update`

5. S'y connecter:

```
gcloud compute ssh $VM_NAME \
  --project $PROJECT_ID \
  --zone $VM_ZONE
```

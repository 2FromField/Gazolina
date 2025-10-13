# Gazolina

![Kubernetes](https://img.shields.io/badge/Kubernetes-3069DE?style=for-the-badge&logo=kubernetes&logoColor=white)
![ArgoCD](https://img.shields.io/badge/Argo%20CD-1e0b3e?style=for-the-badge&logo=argo&logoColor=#d16044)
![Airflow](https://img.shields.io/badge/Airflow-017CEE?style=for-the-badge&logo=Apache%20Airflow&logoColor=white)
![Python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)
![Selenium](https://img.shields.io/badge/Selenium-43B02A?style=for-the-badge&logo=Selenium&logoColor=white)
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

## Pré-requis

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

## ArgoCD

- Créer le namespace & installer le manifest

```
kubectl create namespace argocd
kubectl -n argocd apply -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

- Accéder à l'UI par port-forward (sur la VM): `kubectl -n argocd port-forward svc/argocd-server 8080:443`

- Créer un tunnel pour accéder à l'UI sur votre ordinateur (sur le terminal du PC):

```
gcloud auth login # s'authentifier
gcloud config set project gazolina # setup le projet

# Ouvrir le tunnel
gcloud compute ssh vm-gazolina \
  --project gazolina \
  --zone europe-west1-b \
  -- -N -L 8443:127.0.0.1:8080
```

- S'authentifier avec l'utilisateur "admin" et le password créé: `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo`

## Postgresql

1. Création des fichiers `gitops/apps/postgresql.yaml` & `gitops/components/postgresql/values.yaml`

2. Mettre à jour le fichier `gitops/apps/projects/platform-project.yaml` avec le nouveau chart destiné à la base de données PostgreSQL

## Apps-of-app

1. Mettre en place l'architecture:

- gitops/
  - apps/ # ← le root va pointer ici
    - airflow.yaml # Application Argo CD pour Airflow
    - postgresql.yaml # Application pour la DB PostgreSQL
    - (autres-apps…).yaml
  - projects/
    platform-project.yaml # AppProject (bonnes pratiques)
  - values/
    - airflow/values.yaml # tes values Helm Airflow
- root-app.yaml

2. Créer les fichiers `platform-project.yaml` & `root-app.yaml`

3. Accorder l'accès en SSH à ArgoCD:

- Préparer une deploy key: `ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519_argocd -C "argocd-repo"`
- Récupérer la clé: `cat ~/.ssh/id_ed25519_argocd.pub`
- Générer le secreta avec known_hosts: `ssh-keyscan github.com > /tmp/known_hosts`
- Créer le Secret repository dans argocd:

```
kubectl -n argocd create secret generic repo-gazolina \
  --from-literal=url='git@github.com:2FromField/Gazolina.git' \
  --from-file=sshPrivateKey="$HOME/.ssh/id_ed25519_argocd" \
  --from-file=sshKnownHosts=/tmp/known_hosts

kubectl -n argocd label secret repo-gazolina \
  argocd.argoproj.io/secret-type=repository --overwrite
```

- Vérification:

```
# Présence de la clé privée:
kubectl -n argocd get secret repo-gazolina -o jsonpath='{.data.sshPrivateKey}' | base64 -d | head -n3
```

3. Créer le projet "platform": `kubectl apply -n argocd -f https://raw.githubusercontent.com/2FromField/Gazolina/main/uv_gazolina/gitops/projects/platform-project.yaml`

4. Créer le service "root": `kubectl apply -n argocd -f https://raw.githubusercontent.com/2FromField/Gazolina/main/uv_gazolina/root-app.yaml` & rafraichir: `kubectl -n argocd patch application root   --type merge -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"hard"}}}'`

5. Vérifier que le projet "platform" a été créé: `kubectl -n argocd get appproject`

## Airflow

### Installation

- Préparer l'accès Git pour la git-sync (via SSH):

```
# Génère une clé SANS passphrase (ou réutilise ta deploy-key GitHub)
ssh-keygen -t ed25519 -N "" -f ./id_ed25519 -C "airflow@cluster"
cat ./id_ed25519.pub

# known_hosts GitHub (ed25519) :
ssh-keyscan github.com > ./known_hosts
```

- Créer le namespace pour Airflow: `kubectl create namespace airflow`

- Créer les secrets nécessaires:

```
# Clé SSH du repo GitHub
kubectl -n airflow create secret generic airflow-ssh-secret \
  --from-file=gitSshKey=./id_ed25519 \
  --from-file=known_hosts=./known_hosts

# Clé Fernet
FERNET_KEY=$(head -c 32 /dev/urandom | base64 | tr '+/' '-_' | tr -d '\n')
kubectl -n airflow create secret generic airflow-fernet-key \
  --from-literal=airflow-fernet-key="$FERNET_KEY"

# Clé secret Flask du webserver
kubectl -n airflow create secret generic airflow-webserver-secret-key \
  --from-literal=airflow-webserver-secret-key="$(head -c 16 /dev/urandom | base64 | tr -d '\n')"
```

- Télécharger le fichier:

```
curl -fsSL -o ~/airflow-app.yaml \
  https://raw.githubusercontent.com/2FromField/Gazolina/main/uv_gazolina/helm/airflow-app.yaml
```

- OPTIONNEL: valider le YAML côté client: `kubectl apply --dry-run=client -f ~/airflow-app.yaml`

- Appliquer le fichier YAML: `kubectl apply -f ~/airflow-app.yaml`

---

- Mettre à jour le fichier .yaml: `kubectl apply -n argocd -f https://raw.githubusercontent.com/2FromField/Gazolina/main/uv_gazolina/gitops/apps/airflow.yaml`
- Supprimer le service et le relancer:

```
kubectl -n argocd delete application airflow
```

---

Vérifications:

- Image PostgreSQL (devant être: "docker.io/bitnami/postgresql:16"):

```
kubectl -n airflow get statefulset airflow-postgresql \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

- Vérifier la Job migration:

```
kubectl -n airflow get jobs,pods | grep -i migrate || true
MIGPOD=$(kubectl -n airflow get pod -l job-name=airflow-migrate-database-job -o jsonpath='{.items[0].metadata.name}' 2>/dev/null) || true
[ -n "$MIGPOD" ] && kubectl -n airflow logs "$MIGPOD" --tail=200 || echo "Pas de pod de migration trouvé"
```

Si la sortie retourne "Pas de pod de migration trouvé", alors il faut créer une Job 'one-shot' faisant un `airflow db upgrade`:

```
cat <<'YAML' | kubectl -n airflow apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: airflow-db-migrate
spec:
  backoffLimit: 2
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: migrate
        image: apache/airflow:2.9.3
        command: ["bash","-lc","airflow db migrate"]
        env:
          - name: AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
            value: "postgresql+psycopg2://airflow:airflow@postgresql.database.svc.cluster.local:5432/airflow"
YAML

# Suivre la migration
kubectl -n airflow logs -f job/airflow-db-migrate
```

- Générer le fichier de dépendances 'requirements.txt': `uv pip compile uv_gazolina/pyproject.toml -o uv_gazolina/requirements.txt`

### Configuration des crédentials

1. Créer un fichier `uv_gazolina/pipeline.conf` contenant les credentials

2. Installer Homebrew: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`

3. Installer age & SOPS sur MacOS:

```
brew update
brew install age sops

# Confirmer l'installation en affichant les versions
age --version
sops --version
```

3. Générer une clé de chiffrage SOPS (+ age):

```
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt
PUB=$(age-keygen -y ~/.config/sops/age/keys.txt)
echo "$PUB"
```

4. Chiffrer le fichier 'pipeline.conf' en 'pipeline.conf.enc' avec SOPS et la clé de chiffrement:

```
sops --encrypt --age "$PUB" uv_gazolina/pipeline.conf > uv_gazolina/pipeline.conf.enc
```

5. Créer le manifest de Secret afin de créer un Secret k8s pour ArgoCD:

```
cat > uv_gazolina/gitops/secrets/mongo-pipeline.yaml <<'YAML'
apiVersion: v1
kind: Secret
metadata:
  name: mongo-pipeline
  namespace: airflow
type: Opaque
stringData:
  MONGO_URI: mongodb+srv://user:pass@host/db
  MONGO_USER: user
  MONGO_PASS: pass
YAML
```

6. Chiffrer localement avec SOPS: `sops --encrypt --age "$PUB" -i uv_gazolina/gitops/secrets/mongo-pipeline.yaml`

7. Copier la clé privée age du local vers la VM:

```
mkdir -p ~/.config/sops/age
cat > ~/.config/sops/age/keys.txt <<'EOF'
# colle ici TOUT le contenu affiché sur ton Mac,
# y compris les lignes "# public key: ..." et la ligne AGE-SECRET-KEY-1...
EOF
```

8. Créer le secret dans 'argocd':

```
kubectl -n argocd create secret generic sops-age \
  --from-file=age.agekey=$HOME/.config/sops/age/keys.txt \
  --dry-run=client -o yaml | kubectl apply -f -
```

9. Créer le ConfigMap du plugin CMP:

```
cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmp-cm
  namespace: argocd
data:
  sops-plugin.yaml: |
    apiVersion: argoproj.io/v1alpha1
    kind: ConfigManagementPlugin
    metadata:
      name: sops
    spec:
      version: v1.0
      # Autorise explicitement ton repo (sinon: "plugin ... not supporting the given repository")
      allow:
        repos:
          - https://github.com/2FromField/Gazolina.git
      generate:
        command: [bash, -lc]
        args:
          - |
            set -euo pipefail
            # Déchiffre chaque YAML s'il est chiffré SOPS, sinon le laisse tel quel, puis agrège
            files=$(find . -type f \( -name "*.yaml" -o -name "*.yml" \));
            for f in $files; do
              if sops -d "$f" >/dev/null 2>&1; then sops -d "$f"; else cat "$f"; fi
            done | yq -s cat
YAML
```

10. Monter le secret dans 'argocd-repo-sercer' et redémarrer:

```
kubectl -n argocd create secret generic sops-age \
  --from-file=age.agekey=$HOME/.config/sops/age/keys.txt \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n argocd patch deploy argocd-repo-server --type merge -p '{
  "spec":{"template":{"spec":{
    "volumes":[{"name":"sops-age","secret":{"secretName":"sops-age"}}],
    "containers":[{"name":"argocd-repo-server",
      "volumeMounts":[{"name":"sops-age","mountPath":"/sops"}],
      "env":[{"name":"SOPS_AGE_KEY_FILE","value":"/sops/age.agekey"}]
    }]
  }}}}'
kubectl -n argocd rollout restart deploy/argocd-repo-server
```

11. Ajouter un Config Management Plugin permettant à ArgoCD de déchirer les fichier .yaml SOPS

```
kubectl -n argocd patch configmap argocd-cm --type merge -p '{
  "data": {
    "configManagementPlugins": "- name: sops\n  generate:\n    command: [\"bash\",\"-lc\"]\n    args: [\"set -euo pipefail; files=$(find . -type f \\( -name \\\"*.yaml\\\" -o -name \\\"*.yml\\\" \\)); for f in $files; do if sops -d $f >/dev/null 2>&1; then sops -d $f; else cat $f; fi; done | yq -s cat\"]\n"
  }
}'
kubectl -n argocd rollout restart deploy/argocd-repo-server
```

#### Commandes utiles k8s

| Commade                            |                             Description |
| ---------------------------------- | --------------------------------------: |
| `kubectl get svc --all-namespaces` |    Afficher tous les services installés |
| `kubectl get pods -n airflow`      | Afficher les pods d'un namespace précis |

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

- Si ce n'est pas le bon projet, redéfinir la target: `gcloud config set project gazolina`

3. Vérifier que la vm est bien présente dans le projet:

```
gcloud compute instances list --project gazolina \
  --filter='name=("vm_gazolina")' \
  --format='table(project, name, zone, status, networkInterfaces[].accessConfigs[].natIP)'
```

4. Installation des composants GCP cloud: `gcloud components update`

5. S'y connecter:

```
gcloud compute ssh vm-gazolina \
  --project gazolina \
  --zone europe-west1-b
```

## Modifier la VM

- Augmenter la taille du disque boot:

```
gcloud compute disks resize vm-gazolina \
  --project gazolina \
  --zone europe-west1-b \
  --size 60GB
```

- Modifier l'espace de stockage du `sda1`:

1. Repérer la partition14: `sudo parted -m /dev/sda unit s print`
2. Redimensionner le disque au maximum:

```
sudo parted /dev/sda ---pretend-input-tty <<'EOF'
unit s
print
resizepart 1 100%
Yes
quit
EOF
```

3. Etendre le système de fichiers: `sudo resize2fs /dev/sda1`
4. Afficher les espaces de stockages: `df -h`

## Recréer le cluster minikube de zéro

```
# 1. Tuer le cluster minikube
minikube delete --all --purge || true
docker rm -f minikube 2>/dev/null || true

# 2. Nettoyage réseau/cache
docker network prune -f
sudo systemctl restart docker

# 3. Configurer le nouveau cluster
minikube config set driver docker
minikube config set cpus 4
minikube config set memory 8192
minikube config set disk-size 20g

minikube start --kubernetes-version=v1.30.0 --delete-on-failure -v=1
```

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

2. Optionnel: fixer le fuseau horaire: `sudo timedatectl set-timezone Europe/Paris`

3. Créer un utilisateur système dédié:

```
sudo useradd --system --create-home --home-dir /opt/airflow --shell /bin/bash airflow
sudo mkdir -p /opt/airflow/{dags,logs,plugins}
sudo chown -R airflow:airflow /opt/airflow
```

4. Instanciation de la base de données PostgreSQL:

```
sudo -u postgres psql <<'SQL'
CREATE USER airflow WITH PASSWORD 'airflow';
CREATE DATABASE airflow OWNER airflow;
GRANT ALL PRIVILEGES ON DATABASE airflow TO airflow;
SQL
```

5. Mise en place des fichiers d'environnement Airflow

```
sudo tee /etc/airflow.env >/dev/null <<'ENV'
AIRFLOW_HOME=/opt/airflow
# Executor & DB
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@localhost/airflow
# UI, logs, etc.
AIRFLOW__CORE__LOAD_EXAMPLES=False
AIRFLOW__WEBSERVER__EXPOSE_CONFIG=True
AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags
AIRFLOW__CORE__BASE_LOG_FOLDER=/opt/airflow/logs
AIRFLOW__LOGGING__BASE_LOG_FOLDER=/opt/airflow/logs
AIRFLOW__WEBSERVER__WEB_SERVER_PORT=8080
# (Optionnel) secret key / fernet si tu en as une
# AIRFLOW__CORE__FERNET_KEY=<clé_fernet>
ENV
sudo chown airflow:airflow /etc/airflow.env
sudo chmod 640 /etc/airflow.env
```

6. Ajout des services systemd (webserver + scheduler):

```
sudo tee /etc/systemd/system/airflow-webserver.service >/dev/null <<'UNIT'
[Unit]
Description=Apache Airflow Webserver
After=network.target postgresql.service
Requires=postgresql.service

[Service]
User=airflow
Group=airflow
EnvironmentFile=/etc/airflow.env
ExecStart=/opt/airflow/venv/bin/airflow webserver
Restart=always
RestartSec=5
WorkingDirectory=/opt/airflow
# journalctl affichera les logs
StandardOutput=journal
StandardError=journal
LimitNOFILE=100000

[Install]
WantedBy=multi-user.target
UNIT

sudo tee /etc/systemd/system/airflow-scheduler.service >/dev/null <<'UNIT'
[Unit]
Description=Apache Airflow Scheduler
After=network.target postgresql.service airflow-webserver.service
Requires=postgresql.service

[Service]
User=airflow
Group=airflow
EnvironmentFile=/etc/airflow.env
ExecStart=/opt/airflow/venv/bin/airflow scheduler
Restart=always
RestartSec=5
WorkingDirectory=/opt/airflow
StandardOutput=journal
StandardError=journal
LimitNOFILE=100000

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now airflow-webserver airflow-scheduler
```

7. Vérifier la connexion au compte GCP

```
gcloud auth list # Affiche les compte authentifié
gcloud auth login # Se connecter au compte google
```

8. Créer la base de données et l'utilisateur Admin:

```
# Passer sous l'utilisateur airflow
sudo -iu airflow

# Charger l'env du service et activer le venv
set -a; [ -f /etc/airflow.env ] && . /etc/airflow.env; set +a
source /opt/airflow/venv/bin/activate

# Vérifs
airflow version
echo "AIRFLOW_HOME=$AIRFLOW_HOME"
echo -n "sql_alchemy_conn="; airflow config get-value database sql_alchemy_conn

# Init/migration DB
airflow db init || airflow db migrate

# Créer l'admin (change le mot de passe)
airflow users create \
  --username admin \
  --firstname Admin --lastname User \
  --role Admin --email admin@example.com \
  --password 'password'

# Quitter proprement
deactivate
exit
```

9. Redémarrer les services:

```
sudo systemctl restart airflow-scheduler airflow-webserver
sudo systemctl status  airflow-webserver
```

10. Afficher le statut du webserver: `sudo systemctl status airflow-webserver`

11. Associer l'IP de la VM à l'IP du poste:

```
# Récupérer ton IP publique actuelle
MYIP=$(curl -s ifconfig.me)/32

# Mise en place de la règle
gcloud compute firewall-rules update allow-airflow-8080 \
  --project gazolina \
  --source-ranges="$MYIP"

# Lancer le service
curl -I http://127.0.0.1:8080
```

### DAGs

Migrer le DAGs vers le dossier lisible par Airflow sur la VM:

1. (Ne faire qu'une fois initialement) Créer le dossier d'appel sur la VM: `sudo mkdir -p /opt/airflow/dags`
2. Sur le terminal de votre ordinateur, migrer le dags sur la VM dans le dossier courant **home/$USER**:

```
gcloud compute scp ./uv_gazolina/dags/dag_essence.py \
  vm-gazolina:~/dag_essence.py \
  --project gazolina --zone europe-west1-b
```

_Note_: Si le terminal demande d'entrer une **passphrase**, juste cliquer sur la touche 'Entrer'

3. Se connecter à la VM & migrer le dags python vers le dossier d'appel de la VM:

```
sudo mv dag_essence.py /opt/airflow/dags/
```

4. Actualiser les droits d'auteurs à airflow pour accéder au dossier: `sudo chown -R airflow:airflow /opt/airflow/dags`

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

4. Installation des composants GCP cloud: `gcloud components update`

5. S'y connecter:

```
gcloud compute ssh $VM_NAME \
  --project $PROJECT_ID \
  --zone $VM_ZONE
```

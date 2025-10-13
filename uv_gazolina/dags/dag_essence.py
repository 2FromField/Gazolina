from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
import pendulum

with DAG(
    dag_id="get_essence",
    description="Lance MonEssecence.py tous les jours à 07:00 (Europe/Paris)",
    # Début : 7 octobre 2025 à minuit (le premier run sera à 07:00 ce jour-là)
    start_date=pendulum.datetime(2025, 10, 7, 0, 0, 0),
    schedule="0 7 * * *",  # tous les jours à 07:00
    catchup=False,  # pas de rattrapage automatique avant maintenant
    max_active_runs=1,
    default_args={
        "owner": "airflow",
        "retries": 1,
        "retry_delay": timedelta(minutes=2),
    },
    tags=["prod", "script"],
) as dag:
    run_script = BashOperator(
        task_id="run_get_essence",
        # Utilise le Python du venv Airflow + ton script
        bash_command="python -u /opt/airflow/dags/repo/uv_gazolina/script/MonEssence.py",
        # (Optionnel) passer des variables d'env à ton script
        env={
            "CODE_POSTAL": "02820",  # exemple
            # ajoute ce dont ton script a besoin
        },
    )

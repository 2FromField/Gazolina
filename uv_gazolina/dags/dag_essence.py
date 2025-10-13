from pathlib import Path
from datetime import timedelta
import pendulum
from airflow import DAG
from airflow.operators.python import PythonVirtualenvOperator


# callable exécutée DANS le venv
def run_script(code_postal: str = "02820"):
    import os, sys, runpy, pathlib

    base = pathlib.Path("/opt/airflow/dags/repo/uv_gazolina/scripts")
    # ➜ permet "import utils" car utils.py est dans scripts/
    sys.path.insert(0, str(base))
    os.environ["CODE_POSTAL"] = code_postal
    runpy.run_path(str(base / "MonEssence.py"), run_name="__main__")


def read_requirements(path: str):
    p = Path(path)
    if not p.exists():
        # laisse un message clair dans les logs si git-sync n'a pas encore matérialisé le fichier
        raise FileNotFoundError(f"requirements.txt introuvable: {p}")
    return [
        l.strip()
        for l in p.read_text().splitlines()
        if l.strip() and not l.startswith("#")
    ]


REQ_FILE = "/opt/airflow/dags/repo/uv_gazolina/requirements.txt"
reqs = read_requirements(REQ_FILE)

with DAG(
    dag_id="get_essence",
    description="Lance MonEssence.py tous les jours à 07:00 (Europe/Paris)",
    start_date=pendulum.datetime(2025, 10, 7, 0, 0, 0, tz="Europe/Paris"),
    schedule="0 7 * * *",
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "airflow",
        "retries": 1,
        "retry_delay": timedelta(minutes=2),
    },
    tags=["prod", "script"],
) as dag:
    run = PythonVirtualenvOperator(
        task_id="run_get_essence",
        python_callable=run_script,
        op_kwargs={"code_postal": "02820"},  # <-- remplace l'env du BashOperator
        requirements=reqs,  # <-- installé dans le venv de la task
        system_site_packages=False,  # venv isolé
        # use_dill=True,                      # à activer si tu sérialises des objets complexes
    )

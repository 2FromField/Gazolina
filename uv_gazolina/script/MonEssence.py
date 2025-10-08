from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import polars as pl
from selenium.webdriver.chrome.options import Options
import utils
from pathlib import Path
import time

from pathlib import Path
import time, re
import os
import polars as pl
from pymongo import MongoClient, errors
import configparser

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import utils  # ta fonction accept_consent(driver)

# -----------------------
# Helpers
# -----------------------

FUEL_TO_ID = {
    "GO": "id-gasoil",
    "E10": "id-sp95+e10",
    "SP95": "id-sp95",
    "SP98": "id-sp98",
    "E85": "id-e85",
    "GPL": "id-gpl",
}


def fr_to_float(s: str) -> float | None:
    """Convertit '1,594 €' -> 1.594 ; '11,9 km' -> 11.9 ; retourne None si vide."""
    if not s:
        return None
    s = s.strip().replace("\xa0", " ")
    s = re.sub(r"[^\d,.\-]", "", s)  # garde chiffres/./,/-
    if "," in s and (s.rfind(",") > s.rfind(".")):
        s = s.replace(".", "")
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def select_fuel_and_wait(driver, fuel_code: str, timeout: int = 12):
    """Clique le label du carburant et attend le refresh (URL ou DOM)."""
    fuel_id = FUEL_TO_ID[fuel_code.upper()]
    wait = WebDriverWait(driver, timeout)

    # snapshot avant clic
    results_sel = "main"  # ajuste si tu as un wrapper plus spécifique
    try:
        before = driver.find_element(By.CSS_SELECTOR, results_sel).get_attribute(
            "innerHTML"
        )
    except Exception:
        before = None
    old_url = driver.current_url

    # clic sur le <label for="...">
    lbl = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, f'label[for="{fuel_id}"]'))
    )
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", lbl)
    try:
        lbl.click()
    except Exception:
        driver.execute_script("arguments[0].click();", lbl)

    # attendre: changement d'URL ou du contenu
    try:
        wait.until(EC.url_changes(old_url))
    except Exception:
        if before is not None:
            wait.until(
                lambda d: d.find_element(By.CSS_SELECTOR, results_sel).get_attribute(
                    "innerHTML"
                )
                != before
            )
    time.sleep(0.2)


# -----------------------
# Chemins & schéma
# -----------------------

# Dossier racine du projet = parent du dossier "script"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Credentials
credential_path = PROJECT_ROOT / "pipeline.conf"
parser = configparser.ConfigParser()
parser.read(credential_path)

# Configuration de la base de données MongoDB
MONGO_URI = parser.get("mongodb", "uri")
MONGO_DB = parser.get("mongodb", "db_name")
MONGO_COL = parser.get("mongodb", "collection")

# Chemins de sauvegarde
in_path = PROJECT_ROOT / "data" / "mon_essence.parquet"
in_path.parent.mkdir(parents=True, exist_ok=True)


# Typage des colonnes lors de la création initiale du dataframe
SCHEMA = {
    "date": pl.Utf8,
    "code_postale": pl.Utf8,
    "carburant": pl.Utf8,
    "station": pl.Utf8,
    "ville": pl.Utf8,
    "distance": pl.Float64,
    "prix": pl.Float64,
    "verif": pl.Boolean,
    "lien": pl.Utf8,  # ← utile pour dédup
}

# Charger si présent, sinon créer un parquet vide schématisé
if in_path.exists():
    df = pl.read_parquet(in_path)
else:
    df = pl.DataFrame(schema=SCHEMA)
    df.write_parquet(in_path)  # df est vide

# -----------------------
# Selenium
# -----------------------

# Options relative au webdriver
opts = Options()
opts.add_argument("--headless=new")  # Navigateur caché

# Lancer le Driver avec Chrome
driver = webdriver.Chrome(options=opts)
wait = WebDriverWait(driver, 15)

# Variables
CODE_POSTAL = os.getenv("CODE_POSTAL")

# URL
url = f"https://mon-essence.fr/ville/29383-mauregny-en-haye?q={CODE_POSTAL}"
driver.get(url)

# Accepter le popup des conditions générales
_ = utils.accept_consent(driver)

time.strftime("%d/%m/%Y", time.localtime())  # warm-up
today = time.strftime("%d/%m/%Y", time.localtime())

# Parcourir tous les types de carburants
all_rows = []
for fuel in ["GO", "E10", "SP95", "SP98", "E85", "GPL"]:
    # 1) sélectionner le carburant et attendre le rafraîchissement
    try:
        select_fuel_and_wait(driver, fuel)
    except Exception as e:
        print(f"[{fuel}] échec sélection: {e}")
        continue

    # 2) scraper les cartes de la page courante
    cards = driver.find_elements(
        By.CSS_SELECTOR, 'a.row.text-decoration-none.text-dark[href^="/station/"]'
    )
    for c in cards:

        def safe_text(sel):
            try:
                return c.find_element(By.CSS_SELECTOR, sel).text.strip()
            except Exception:
                return None

        price_txt = safe_text("span.fs-1.fw-medium")
        dist_txt = safe_text("div.d-flex.align-items-center p.small")
        verif_txt = safe_text("span.text-success.small.fw-medium")

        all_rows.append(
            {
                "date": today,
                "code_postale": CODE_POSTAL,
                "carburant": fuel,
                "station": safe_text("h2"),
                "ville": safe_text("span.small.text-gray-500.fw-light"),
                "distance": fr_to_float(dist_txt),  # "11,9 km" -> 11.9
                "prix": fr_to_float(price_txt),  # "1,594 €" -> 1.594
                "verif": bool(verif_txt and "Vérifié" in verif_txt),
                "lien": c.get_attribute("href"),
            }
        )

# Fermer la page web
driver.quit()

# -----------------------
# Construction & sauvegarde
# -----------------------

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
col = client[MONGO_DB][MONGO_COL]

# Insère la liste de dicts
try:
    res = col.insert_many(all_rows, ordered=False)  # ordered=False = plus rapide
    print(f"MongoDB: insérés = {len(res.inserted_ids)}")
except errors.BulkWriteError as e:
    # si certains docs sont invalides/dupliqués, on le voit ici
    print(f"MongoDB: insérés partiellement (nInserted={e.details.get('nInserted',0)})")

client.close()

"""
# Construire new_df, forcer le schéma/ordre des colonnes
new_df = pl.from_dicts(all_rows)
# ajouter les colonnes manquantes pour respecter SCHEMA
for col, dtype in SCHEMA.items():
    if col not in new_df.columns:
        new_df = new_df.with_columns(pl.lit(None).cast(dtype).alias(col))
new_df = new_df.select(list(SCHEMA.keys())).cast(SCHEMA, strict=False)

# Concat + dédup (évite doublons si relance)
df = pl.concat([df, new_df], how="diagonal", rechunk=True).unique(
    subset=["date", "code_postale", "carburant", "lien"], keep="last"
)

# Sauvegarder les données au format parquet
# df.write_parquet(in_path, compression="zstd")
"""

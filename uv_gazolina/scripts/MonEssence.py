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

import sys
import utils  # ta fonction accept_consent(driver)

# -----------------------
# Helpers
# -----------------------

sys.path.insert(0, str(Path(__file__).resolve().parent))

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

# Configuration de la base de données MongoDB
MONGO_URI = "mongodb+srv://jobrulearning_db_user:ZIDaj5jwIFii8zPc@gazolinacluster.uhsoiuq.mongodb.net/"
MONGO_DB = "gazolinadb"
MONGO_COL = "fuel_data"

# Typage des colonnes lors de la création initiale du dataframe
SCHEMA = {
    "date": pl.Utf8,
    "postal_code": pl.Utf8,
    "fuel": pl.Utf8,
    "station": pl.Utf8,
    "city": pl.Utf8,
    "price": pl.Float64,
    "checking": pl.Boolean,
    "link": pl.Utf8,  # ← utile pour dédup
    "lat": pl.Float64,
    "lon": pl.Float64,
    "adress": pl.Utf8,
}

# -----------------------
# Selenium
# -----------------------

# Options relative au webdriver
opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")

# Lancer le Driver avec Chrome
driver = webdriver.Remote(
    command_executor="http://selenium-chrome.airflow.svc.cluster.local:4444",
    options=opts,
)

# Variables
CODE_POSTAL = os.getenv("CODE_POSTAL")

wait = WebDriverWait(driver, 15)

# URL
url = f"https://mon-essence.fr/ville/29383-mauregny-en-haye?q=02820"
driver.get(url)

# Accepter le popup des conditions générales
_ = utils.accept_consent(driver)

time.strftime("%d/%m/%Y", time.localtime())  # warm-up
today = time.strftime("%d/%m/%Y", time.localtime())

# Parcourir tous les types de carburants
full_rows = []
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

        all_rows = {
            "date": today,
            "postal_code": CODE_POSTAL,
            "fuel": fuel,
            "station": safe_text("h2"),
            "city": safe_text("span.small.text-gray-500.fw-light"),
            "price": fr_to_float(price_txt),  # "1,594 €" -> 1.594
            "checking": bool(verif_txt and "Vérifié" in verif_txt),
            "link": c.get_attribute("href"),
        }

        import json, time, urllib.parse, urllib.request

        def geocode_ban(query, limit=1):
            base = "https://api-adresse.data.gouv.fr/search/"
            params = {"q": query, "limit": limit}
            url = base + "?" + urllib.parse.urlencode(params)

            # (User-Agent pas obligé, mais c'est bien pratique pour tracer)
            req = urllib.request.Request(url, headers={"User-Agent": "uv-gazolina/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            feats = data.get("features", [])
            results = []
            for f in feats:
                # BAN -> geometry.coordinates = [lon, lat]
                lon, lat = f["geometry"]["coordinates"]
                label = f["properties"].get("label")
                results.append({"lat": float(lat), "lon": float(lon), "label": label})
            return results

        # Exemple d’appel (ton cas)
        rows = geocode_ban(
            f"{all_rows['station']} {all_rows['city']} France {all_rows['postal_code']}",
            limit=1,
        )

        query = f"{all_rows.get('station','')} {all_rows.get('city','')} France".strip()
        res = geocode_ban(query, limit=1)
        if res:
            all_rows["lat"] = res[0]["lat"]
            all_rows["lon"] = res[0]["lon"]
            all_rows["adress"] = res[0]["label"]
        else:
            all_rows["lat"] = all_rows["lon"] = None
            all_rows["adress"] = None

        full_rows.append(all_rows)

# Fermer la page web
driver.quit()

# -----------------------
# Construction & sauvegarde
# -----------------------

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
col = client[MONGO_DB][MONGO_COL]

# Insère la liste de dicts
try:
    res = col.insert_many(full_rows, ordered=False)  # ordered=False = plus rapide
    print(f"MongoDB: insérés = {len(res.inserted_ids)}")
except errors.BulkWriteError as e:
    # si certains docs sont invalides/dupliqués, on le voit ici
    print(f"MongoDB: insérés partiellement (nInserted={e.details.get('nInserted',0)})")

client.close()

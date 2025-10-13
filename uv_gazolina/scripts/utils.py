from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
)


def _xpath_literal(s: str) -> str:
    """
    Retourne un littéral XPath sûr, même si `s` contient des apostrophes.
    Ex: J'accepte -> concat('J', "'", 'accepte')
    """
    if "'" not in s:
        return f"'{s}'"
    parts = s.split("'")
    return "concat(" + ', "\'", '.join([f"'{p}'" for p in parts]) + ")"


def _click_button_in_context(driver, timeout=5) -> bool:
    wait = WebDriverWait(driver, timeout)
    texts = [
        "Autoriser",
        "Valider",
        "Tout accepter",
        "J'accepte",
        "Accepter et fermer",
        "Accepter",
    ]

    # 1) Essais par texte exact (dans <button> ou <p> enfant)
    for t in texts:
        lit = _xpath_literal(t)
        xpath = (
            f"//button[.//p[normalize-space()={lit}] or normalize-space()={lit}]"
            f"|//p[normalize-space()={lit}]/ancestor::button"
        )
        try:
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            try:
                btn.click()
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", btn)
            return True
        except TimeoutException:
            continue

    # 2) Fallback par classes Funding Choices
    for sel in [
        ".fc-button.fc-cta-consent",
        ".fc-button.fc-primary-button",
        "button[aria-label='Autoriser']",
        "button[aria-label='Tout accepter']",
    ]:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            driver.execute_script("arguments[0].click();", btn)
            return True
        except NoSuchElementException:
            continue

    return False


def accept_consent(driver, timeout=10) -> bool:
    """Clique sur le bouton de consentement (souvent dans une iframe), puis revient au contexte par défaut."""
    wait = WebDriverWait(driver, timeout)

    # A) Essayer sans iframe
    try:
        if _click_button_in_context(driver, timeout=2):
            return True
    except Exception:
        pass

    # B) Essayer les iframes probables (Funding Choices, Sourcepoint, génériques)
    iframe_selectors = [
        'iframe[src*="fundingchoices"]',
        'iframe[id^="sp_message_iframe_"]',
        'iframe[title*="consent"]',
        'iframe[src*="consent"]',
    ]
    frames = []
    for sel in iframe_selectors:
        frames.extend(driver.find_elements(By.CSS_SELECTOR, sel))

    # Tenter d'abord les probables…
    for frame in frames:
        try:
            driver.switch_to.frame(frame)
            if _click_button_in_context(driver, timeout=3):
                driver.switch_to.default_content()
                # attendre disparition potentielle de l’overlay
                try:
                    wait.until(
                        EC.invisibility_of_element_located(
                            (By.CSS_SELECTOR, 'iframe[src*="fundingchoices"]')
                        )
                    )
                except TimeoutException:
                    pass
                return True
        finally:
            driver.switch_to.default_content()

    # … puis toutes les iframes restantes
    for frame in driver.find_elements(By.TAG_NAME, "iframe"):
        try:
            driver.switch_to.frame(frame)
            if _click_button_in_context(driver, timeout=2):
                driver.switch_to.default_content()
                return True
        finally:
            driver.switch_to.default_content()

    return False

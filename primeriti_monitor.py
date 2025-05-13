import hashlib
import logging
import os
import time

import requests
import yaml
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3 import Retry

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


def load_config(path="config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)


config = load_config()
BOT_TOKEN = str(os.getenv("MAIN_BOT_TOKEN", ""))
CHAT_ID = str(os.getenv("MAIN_CHAT_ID", ""))
BOT_DEBUG_TOKEN = str(os.getenv("DEBUG_BOT_TOKEN", ""))
CHAT_DEBUG_ID = str(os.getenv("DEBUG_CHAT_ID", ""))
SEARCH_KEYWORDS = config["search_keywords"]
HOME_URL = config["urls"]["home"]
SEARCH_URL_TEMPLATE = config["urls"]["search_template"]
HOME_SELECTOR = config["selectors"]["home"]
SEARCH_SELECTOR = config["selectors"]["search"]
IGNORE_SELECTORS = config["selectors"]["ignore"]

session = requests.Session()
retries = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))
HASH_DIR = "hashes"
os.makedirs(HASH_DIR, exist_ok=True)

print(f"Token length: {len(BOT_TOKEN)}, type: {type(BOT_TOKEN)}")
print(f"Chat ID length: {len(CHAT_ID)}, type: {type(CHAT_ID)}")



def get_hash(content):
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def send_telegram(message, chat_id, bot_token):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    response = requests.post(url, data=payload)
    print(response)
    return response.text


def get_previous_hash(identifier):
    file_path = os.path.join(HASH_DIR, f"{identifier}.txt")
    try:
        with open(file_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def save_new_hash(identifier, hash_value):
    file_path = os.path.join(HASH_DIR, f"{identifier}.txt")
    with open(file_path, "w") as f:
        f.write(hash_value)


def get_page_text(url: str, selector: str = None, ignore_selectors=None) -> str:
    if ignore_selectors is None:
        ignore_selectors = []
    cookies = {'store': 'primeritiStore', 'locale': 'es_ES'}
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8", "Referer": "https://www.primeriti.es/", }
    retries = 3
    for attempt in range(retries):
        try:
            response = session.get(url, headers=headers, cookies=cookies, timeout=15)
            response.raise_for_status()
            break
        except requests.exceptions.Timeout:
            logging.warning(f"[TIMEOUT] Attempt {attempt + 1}/{retries} - Timed out while fetching: {url}")
            if attempt < retries - 1:
                time.sleep(5)
            else:
                return ""
        except requests.exceptions.RequestException as e:
            logging.error(f"[ERROR] Request failed for {url}: {e}")
            return ""
    soup = BeautifulSoup(response.text, "html.parser")
    # Remove dynamic content like countdown timers
    for ignore_selector in ignore_selectors:
        for element in soup.select(ignore_selector):
            element.decompose()  # Remove the element
    if selector:
        section = soup.select_one(selector)
        return section.get_text(strip=True) if section else ""
    return soup.get_text(strip=True)


def check_and_notify(identifier, url, selector, notify_message, ignore_if_contains=None, ignore_selectors=None):
    page_text = get_page_text(url, selector, ignore_selectors)
    if ignore_if_contains and ignore_if_contains in page_text:
        return  # If no results, return early
    current_hash = get_hash(page_text)
    old_hash = get_previous_hash(identifier)
    if current_hash != old_hash:
        save_new_hash(identifier, current_hash)
        send_telegram(notify_message, bot_token=BOT_TOKEN, chat_id=CHAT_ID)
    else:
        message = f"✅✅✅No hay cambios para la búsqueda: {identifier}."
        send_telegram(message, bot_token=BOT_DEBUG_TOKEN, chat_id=CHAT_DEBUG_ID)
        logging.info(message)


def main():
    check_and_notify(identifier="homepage", url=HOME_URL, selector=HOME_SELECTOR, ignore_selectors=IGNORE_SELECTORS,
                     notify_message=f"⚠️🆕⚠️Primeriti: Nuevas ofertas en la web! \n{HOME_URL}")
    for keyword in SEARCH_KEYWORDS:
        search_url = SEARCH_URL_TEMPLATE.format(query=keyword.replace(" ", "+"))
        notify_msg = f"⚠️🔎⚠️Nuevos resultados para: '{keyword}'\n{search_url}"
        check_and_notify(identifier=f"search_{keyword.replace(' ', '_')}", url=search_url,
                         selector=SEARCH_SELECTOR, notify_message=notify_msg,
                         ignore_if_contains='No hemos encontrado resultados para tu búsqueda')


if __name__ == "__main__":
    main()

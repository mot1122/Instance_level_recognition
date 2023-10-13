import re, traceback
from app.scraping.src.utils.util import *
import pandas as pd

import logging
import logging.config
from yaml import safe_load

with open("../conf/logging.yml") as f:
    cfg = safe_load(f)
logging.config.dictConfig(cfg)
logger = logging.getLogger("main")

        
# def extract_entity_ids(ids_file):
#     try:
#         ids = pd.read_csv(ids_file)["wikidata_id"]
#         logger.info(f"len(ids): {len(ids)}")
#         return ids
#     except Exception:
#         traceback.print_exc()

def extract_wikipedia_url(entity_id):
    try:
        wikidata_url = f"https://www.wikidata.org/wiki/{entity_id}"
        soup = parse_to_soup(wikidata_url)
        wikipedia_url = soup.find(href=re.compile("^https://en.wikipedia.org/wiki/")).attrs["href"]
        logger.info(f"wikipedia_url: {wikipedia_url}")
        return wikipedia_url
    except Exception:
        traceback.print_exc()

def fetch_article(wikipedia_url):
    try:
        soup = parse_to_soup(wikipedia_url)
        p_tags = soup.find_all('p')
        article = "\n".join([tag.get_text().strip() for tag in p_tags])
        return article
    except Exception:
        traceback.print_exc()

def download_article(entity_id, category_dir):
    logger.info(f"entity_id: {entity_id}")
    wikipedia_url = extract_wikipedia_url(entity_id)
    article = fetch_article(wikipedia_url)
    if article:
        with open(f"{category_dir}/wikipedia/{entity_id}.txt", "w") as f:
            f.write(article) 


data_dir = f"../../../data/clean"
categories = ["aircraft", "athlete", "bird", "bread", "car", "director", "dog", "us_politician"]
for category in categories:
    category_dir = f"{data_dir}/{category}"
    ids_file = f"{category_dir}/csv/ids.csv"
    ids = pd.read_csv(ids_file)["wikidata_id"]
    logger.info(f"len(ids): {len(ids)}")
    # entity_ids = extract_entity_ids(ids_file)
    make_dir(f"{category_dir}/wikipedia")
    for id in ids:
        download_article(id, category_dir)
        print()
from bs4 import BeautifulSoup
import re, os, pathlib, traceback
import mysql.connector
from util import *

import logging
import logging.config
from yaml import safe_load

with open("../conf/logging.yml") as f:
    cfg = safe_load(f)
logging.config.dictConfig(cfg)
logger = logging.getLogger("main")

# Change
# - database

mysql_user = os.environ["MYSQL_USER"]
mysql_password = os.environ["MYSQL_PASS"]
host = os.environ["DB_HOST"]
# database = "Aircraft_by_popular_name"
# database = "Sportspeople_by_name"
# database = "Gallery_pages_of_birds"
# database = "Breads_by_name"
# database = "Automobiles_by_brand_by_model"
# database = "Film_directors_by_name"
database = "Politicians_of_the_United_States_by_name"
connection = mysql.connector.connect(user=mysql_user, password=mysql_password, host=host, database=database, port=3306)

cur = connection.cursor()
cur.execute("SELECT wikidata_id, img_url FROM img_urls")
img_urls_in_db = cur.fetchall()
img_urls_in_db = set([(wikidata_id, img_url) for (wikidata_id, img_url) in img_urls_in_db])
cur.execute("SELECT wikidata_id FROM names")
wikidata_ids_in_db = cur.fetchall()
wikidata_ids_in_db = set([wikidata_id for (wikidata_id,) in wikidata_ids_in_db])

def extract_next_page_url(url, text="next page"):
    res = fetch(url)
    soup = BeautifulSoup(res.text, "html.parser")
    try:
        t = soup.find(text=text)
        if t:
            return to_abs_url(related_url=t.parent.attrs["href"])
    except Exception:
        traceback.print_exc()
        return None


def extract_entity_id(entity_url):
    try:
        res = fetch(entity_url)
        soup = BeautifulSoup(res.text, "html.parser")
        wikidata_url = soup.find(href=re.compile("^https://www.wikidata.org/wiki/Q")).attrs["href"]
        wikidata_id = pathlib.Path(wikidata_url).stem
        return wikidata_id
    except Exception:
        print(f"in {entity_url}")
        traceback.print_exc()
        return None


def make_entity_img_dir(id):
    img_path = "../data_aircraft/imgs/" + id  # Change this line
    if not os.path.isdir(img_path):
        os.makedirs(img_path)
    return img_path


def extract_image_url(img_page_url):
    try:
        res = fetch(img_page_url)
        soup = BeautifulSoup(res.text, "html.parser")
        l = soup.find(class_="fullImageLink")
        if l:
            img_url = l.a.attrs["href"]
            return img_url
        else:
            print("can't extract image URL")  # for example, in the case that the file is mp3
    except Exception:
        traceback.print_exc()
        return None


def extract_image_urls(entity_img_list_page_url):
    """
    Image Page is the page which contains an image, description, bottons, etc.
    after extract Image Page URL, extract image url from this Page
    """
    first_page = True
    while entity_img_list_page_url:
        res = fetch(entity_img_list_page_url)
        soup = BeautifulSoup(res.text, "html.parser")
        try:
            image_classes = soup.find_all(class_="galleryfilename galleryfilename-truncate")
            if first_page and len(image_classes) < 5:
                logger.info(f"{entity_img_list_page_url} has only {len(image_classes)} images")
                return
            for image_class in image_classes:
                img_page_url = to_abs_url(related_url=image_class.attrs["href"])
                img_url = extract_image_url(img_page_url)
                if img_url:
                    yield img_url
                else:
                    continue
        except Exception:
            traceback.print_exc()
        entity_img_list_page_url = extract_next_page_url(entity_img_list_page_url)
        first_page = False


def download_image(url, file_path, wikidata_id):
    res = fetch(url)
    if res:
        logger.info(file_path)
        with open(file_path, "wb") as f:
            f.write(res.content)

        insert_new_img_url = "INSERT INTO img_urls (wikidata_id, img_url) " "VALUE (%s, %s)"
        insert_new_img_wikidata_id = "INSERT INTO img_wikidata_id (img_id, wikidata_id) " "VALUES (%s, %s)"
        insert_new_img_path = "INSERT INTO img_path (img_id, path) " "VALUES (%s, %s)"

        try:
            print(file_path)
            cur.execute(insert_new_img_url, (wikidata_id, url))
            img_urls_in_db.add((wikidata_id, url))
            img_id = cur.lastrowid
            cur.execute(insert_new_img_wikidata_id, (img_id, wikidata_id))
            cur.execute(insert_new_img_path, (img_id, file_path))
            connection.commit()
        except Exception:
            traceback.print_exc()


def download_images(entity_name, entity_url):
    wikidata_id = extract_entity_id(entity_url)
    if not wikidata_id:
        return
    logger.info(f"{entity_name}, {entity_url}")
    insert_new_name = "INSERT INTO names (wikidata_id, name) " "VALUES (%s, %s)"
    if wikidata_id not in wikidata_ids_in_db:
        cur.execute(insert_new_name, (wikidata_id, entity_name))
        wikidata_ids_in_db.add(wikidata_id)
    else:  # For scraping from the middle
        logger.info(f"Still exists {entity_name}, {entity_url}")
        return

    img_dir_path = make_entity_img_dir(wikidata_id)
    for i, img_url in enumerate(extract_image_urls(entity_url)):
        if (wikidata_id, img_url) in img_urls_in_db:
            print(f"still exists: ({wikidata_id}, {img_url})")
            continue
        filename = "image_" + str(i).zfill(4) + ".jpg"
        img_file_path = os.path.join(img_dir_path, filename)
        download_image(url=img_url, file_path=img_file_path, wikidata_id=wikidata_id)


def extract_entity_urls_for_gallery(category):
    entity_list_page_url = to_abs_url(related_url=f"/wiki/Category:{category}")

    while entity_list_page_url:
        res = fetch(entity_list_page_url)
        soup = BeautifulSoup(res.text, "html.parser")

        try:
            groups = soup.find_all(class_="mw-category-group")
            for group in groups:
                elems = group.find_all("li")
                for elem in elems:
                    entity_name = elem.find("a").text
                    entity_url = to_abs_url(related_url=elem.find("a").attrs["href"])
                    if entity_name and entity_url:
                        yield entity_name, entity_url
                    else:
                        continue
        except Exception:
            traceback.print_exc()

        entity_list_page_url = extract_next_page_url(entity_list_page_url)


def extract_entity_urls(category):
    entity_list_page_url = to_abs_url(related_url=f"/wiki/Category:{category}")

    while entity_list_page_url:
        res = fetch(entity_list_page_url)
        soup = BeautifulSoup(res.text, "html.parser")

        try:
            elems = soup.find_all(class_="CategoryTreeItem")
            for elem in elems:
                entity_name = elem.find("a").text
                entity_url = to_abs_url(related_url=elem.find("a").attrs["href"])
                if entity_name and entity_url:
                    yield entity_name, entity_url
                else:
                    continue
        except Exception:
            traceback.print_exc()

        entity_list_page_url = extract_next_page_url(entity_list_page_url)

# If there are subcategories, execute following codes.
# def extract_categories(category):
#     category_list_page_url = to_abs_url(related_url=f"/wiki/Category:{category}")

#     while category_list_page_url:
#         res = fetch(category_list_page_url)
#         soup = BeautifulSoup(res.text, "html.parser")

#         try:
#             elems = soup.find_all(class_="CategoryTreeItem")
#             for elem in elems:
#                 category_name = elem.find("a").text
#                 category_url = to_abs_url(related_url=elem.find("a").attrs["href"])
#                 if category_name and category_url:
#                     yield category_name, category_url
#                 else:
#                     continue
#         except Exception:
#             traceback.print_exc()

#         category_list_page_url = extract_next_page_url(category_list_page_url)


categories = [(database, None)]
# If there are subcategories, execute following codes.
# categories = extract_categories(database)
# categories = extract_entity_urls(database) # For car

for category, _ in categories:
    # entity_names_urls = extract_entity_urls_for_gallery(category=category) # For bird
    entity_names_urls = extract_entity_urls(category=category)
    for entity_name, entity_url in entity_names_urls:
        download_images(entity_name, entity_url)

connection.close()

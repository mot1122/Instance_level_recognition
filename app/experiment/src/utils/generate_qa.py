import os, pickle, textwrap, traceback, shutil
import openai
from util import *

from dotenv import load_dotenv
load_dotenv()
openai.organization = os.getenv("OPENAI_ORGANIZATION")
openai.api_key = os.getenv("OPENAI_API_KEY")

import logging
import logging.config
from yaml import safe_load

with open("../conf/logging.yml") as f:
    cfg = safe_load(f)
logging.config.dictConfig(cfg)
logger = logging.getLogger("main")

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
) 

data_dir = "../../../data/clean"

@retry(
    retry=retry_if_exception_type((openai.error.APIError, openai.error.APIConnectionError, openai.error.RateLimitError, openai.error.ServiceUnavailableError, openai.error.Timeout)), 
    wait=wait_random_exponential(min=1, max=60), 
    stop=stop_after_attempt(6), 
)
def generate_qa(entity_name, article):
    try:
        messages = [
            {"role": "system", "content": "You are a helpful annotator of wikipedia articles."},
            {"role": "user", "content": textwrap.dedent(f"""
                Generate ten pairs of QA based on the article. Each question must contain the entity name. Use the following format:
                Q: Where was Thomas Flögel born?
                A: Vienna.
                
                Q: Which club did Thomas Flögel play for in Scotland?
                A: Heart of Midlothian.
                
                Q: How many league titles did Thomas Flögel win with Austria Wien?
                A: Three consecutive league titles.
                
                Q: Which club did Thomas Flögel return to after playing abroad?
                A: FK Austria.
                
                Q: What position did Thomas Flögel play during his time with Hearts?
                A: He played in every outfield position.
                """)},
            {"role": "assistant", "content": f"Entity name: {entity_name}"},
            {"role": "assistant", "content": f"Article:\n{article}"},
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0,
        )
        return response.choices[0]["message"]["content"]
    except Exception as e:
        print(f"entity_name: {entity_name}")
        print(f"article: {article}")
        traceback.print_exc()

def generate_qa_by_categories(categories, start_idx=0, end_idx=5000):
    for category in categories:
        logger.info(f"category: {category}")
        category_dir = f"{data_dir}/{category}"
        with open(f"{category_dir}/id_to_name.json") as f:
            id_to_name = json.load(f)
        # with open(f"{category_dir}/id_to_name.json", 'rb') as f:
        #     id_to_name = pickle.load(f)
        
        # limitを用いてid取得数の上限を設定していたが不要になる可能性が高い
        # if limit:
        #     entity_text_files = os.listdir(f"{category_dir}/wikipedia")[:limit]
        # else:
        entity_text_files = os.listdir(f"{category_dir}/wikipedia")

        logger.info(f"len(entity_text_files): {len(entity_text_files)}")

        output_dir = f"{category_dir}/gpt_3_output"
        # if os.path.exists(output_dir):
        #     shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        # TODO: idsの取得のために、jsonとentity_text_filesの両方を使っているが、どちらか一方に統一した方が良い
        logger.info(f"start_idx, endidx: {start_idx}, {end_idx}")
        for i, entity_text_file in enumerate(entity_text_files[start_idx:end_idx]):
            try:
                entity_id = entity_text_file.split(".")[0]
                logger.info(f"Generate questions for {entity_id} ({i+1}/{len(entity_text_files)})")
                if os.path.exists(f"{output_dir}/{entity_text_file}"):
                    logger.info(f"Skip {entity_id} because already generated")
                    continue
                with open(f"{category_dir}/wikipedia/{entity_text_file}") as f:
                    article = f.read()
                    input_text = customize_text(article)
                    output = generate_qa(id_to_name[entity_id], input_text)
                    if output:
                        try:
                            with open(f"{output_dir}/{entity_text_file}", 'w') as f:
                                f.write(output)
                        except Exception:
                            print(f"entity_id: {entity_id}")
                            print(f"output: {output}")
                            traceback.print_exc()
            except Exception:
                print(f"entity_text_file: {entity_text_file}")
                traceback.print_exc()

def main():
    categories = ["athlete"]
    # categories = ["aircraft", "athlete", "bird", "bread", "car", "director", "dog", "us_politician"]
    generate_qa_by_categories(categories)

if __name__ == "__main__":
    main()


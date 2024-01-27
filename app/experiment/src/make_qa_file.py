import sys
sys.path.append("utils")

from generate_qa import generate_qa_by_category
from convert_qa_text_to_json import convert_text_to_dict_by_category
from mask_question import mask_questions_by_category
from rephrase_question import rephrase_questions_by_category
from answer import answer_by_category

import logging
import logging.config
from yaml import safe_load

with open("../conf/logging.yml") as f:
    cfg = safe_load(f)
logging.config.dictConfig(cfg)
logger = logging.getLogger("main")


# カテゴリごとにそれぞれの処理を行っているのは、カテゴリごとに処理を分けることで、処理速度を改善するため
# しかしこれがどの程度効果があるのかは不明
# それぞれのエンティティごとに一気に処理を行っても良いかもしれない。こちらの方がコードが簡潔になる
# 多段で行った方がそれぞれの処理結果を確認しやすいが、これはあくまでテストでそうしている。一気にやってもコメントアウトなどを適宜行うことで、同じことができる

# 8時間で5000エンティティが目安

# Progress: 
# 全てのカテゴリでw/o oracleのbem中

def main():
    patterns = [
        {"name": False, "article": False, "relations": False, "confidence": False},
        {"name": True, "article": False, "relations": False, "confidence": False}, 
        {"name": True, "article": True, "relations": False, "confidence": False}, 
        {"name": True, "article": False, "relations": True, "confidence": False}, 
        {"name": True, "article": True, "relations": True, "confidence": False}, 
        # {"name": True, "article": True, "relations": True, "confidence": True}, 
    ]
    # categories = ["athlete"]
    # categories = ["aircraft", "athlete", "bird", "bread", "car", "director", "dog", "us_politician"]
    category = sys.argv[1] # "aircraft"
    mode = sys.argv[2] # gen, convert, ans
    start_idx = 0
    end_idx = 3
    ans_mode = "oracle"

    # if mode == "gen" or mode == "convert":
    #     # エンティティ数が多いものに関しては、並列処理を行う
    #     if len(sys.argv) >= 5:
    #         start_idx = int(sys.argv[3])
    #         end_idx = int(sys.argv[4])

    # elif mode == "ans":
    #     # 高速化のため、patternのインデックスを指定し、5つを並行実行できるようにした
    #     # patternを1まとめで実行するか、ここで実行をするかを選択する
    #     pattern_mode = sys.argv[3]
    #     if pattern_mode == "split":
    #         pattern_idx = int(sys.argv[4]) # splitの場合はpattern_idxを指定することが必須
    #         patterns = [patterns[pattern_idx]] # pattern_idx = 0, 1, 2, 3, 4のいずれか
    #     # 今のところ必要な処理は存在しないが、一応splitせずに全てのパターンをまとめて行うということ明示するためにallを指定する
    #     elif pattern_mode == "all":
    #         pass
    #         # if len(sys.argv) >= 7:
    #         start_idx = int(sys.argv[4])
    #         end_idx = int(sys.argv[5])
    #         # if len(sys.argv) >= 8:
    #         ans_mode = sys.argv[6]

    if mode == "gen":
        logger.info("Start generate_qa_by_categories ...")
        # idをファイル名として保存するため、splitごとにファイルを上書き保存することはない
        generate_qa_by_category(category, start_idx, end_idx)
    
    elif mode == "conv":
        # 重要: ここから先はsplitごとに上書き保存しないように、出力ファイルをqa_{start_idx}.jsonとし、最後に結合する
        # generate_qa_by_categoriesで生成したgpt-3_output上のファイルを参照し、それぞれの分割ごとにqa_{start_idx}.jsonとして出力
        logger.info("Start convert_text_to_dict_by_categories ...")
        convert_text_to_dict_by_category(category, start_idx, end_idx)

    elif mode == "reph":
        # CAUTION: ここから先はsplitごとに保存されたqaファイルがあることを前提としている
        logger.info("Start rephrase_questions_by_categories ...")
        rephrase_questions_by_category(category, start_idx, end_idx)
        
    elif mode == "mask":
        logger.info("Start mask_entity_name_by_categories ...")
        mask_questions_by_category(category, start_idx,end_idx)
    
    elif mode == "ans":
        logger.info("Start answer_by_categories ...")
        answer_by_category(category, patterns, mode=ans_mode, start_idx=start_idx, end_idx=end_idx)
        # if len(sys.argv) >= 5:
        #     answer_by_category(categories, patterns, mode=ans_mode, start_idx=start_idx, end_idx=end_idx)
        # else:
        #     answer_by_category(categories, patterns, mode=ans_mode)

    logger.info("Finish")


if __name__ == "__main__":
    main()

"""神话传说：盘古开天、女娲补天、后羿射日、嫦娥奔月……老祖宗讲了几千年的故事。
跟孙辈讲讲，既有趣又传文化。纯数据 + 纯逻辑、可单测。可在 config 加。
"""

from __future__ import annotations

_MYTHS = {
    "盘古开天": "天地本是混沌一团，盘古抡起大斧劈开——清气上升成了天，浊气下沉成了地，他死后化作山川草木。",
    "女娲补天": "天塌了个窟窿，女娲炼五彩石把天补好，又斩鳌足撑住四方；传说她还抟黄土造了人。",
    "后羿射日": "天上突然出了十个太阳，晒得万物枯焦，神射手后羿一连射下九个，只留一个，天下才太平。",
    "嫦娥奔月": "后羿的妻子嫦娥吃下不死药，身子轻飘飘飞上了月亮，住进广寒宫；中秋望月就念着她。",
    "精卫填海": "炎帝的小女儿在东海淹死，化作精卫鸟，天天衔石子木枝去填海，比喻坚持不懈、矢志不渝。",
    "夸父逐日": "巨人夸父追赶太阳，一路喝干了黄河渭水还是渴，倒下了；他的手杖化成一片桃林。",
    "牛郎织女": "牛郎织女隔着银河遥遥相望，每年七月初七，喜鹊搭起鹊桥让他们相会——就是七夕。",
    "大禹治水": "大禹治理滔天洪水，改堵为疏、开山导流，三过家门而不入，终于把水患治好。",
    "愚公移山": "愚公家门前两座大山挡路，他带子孙挖山不止，‘子子孙孙无穷匮也’，感动天帝把山搬走了。",
    "白蛇传": "白娘子与许仙相爱，法海从中作梗，水漫金山、断桥相会，最后被压雷峰塔下，是凄美的爱情传说。",
    "牛郎织女鹊桥": "七夕夜喜鹊搭桥，让被银河分隔的牛郎织女相会一面。",
    "八仙过海": "八位神仙过东海，各凭一样宝贝渡海，‘八仙过海，各显神通’说的就是它。",
    "哪吒闹海": "小英雄哪吒大闹龙宫、抽了龙筋，闯祸后剔骨还父、削肉还母，又借莲花重生。",
    "嫦娥": "后羿之妻，奔月住进广寒宫，与玉兔为伴。",
}

_ALIAS = {"盘古": "盘古开天", "女娲": "女娲补天", "后羿": "后羿射日", "精卫": "精卫填海",
          "夸父": "夸父逐日", "大禹": "大禹治水", "愚公": "愚公移山", "白娘子": "白蛇传",
          "牛郎": "牛郎织女", "织女": "牛郎织女", "哪吒": "哪吒闹海"}


def _table(config) -> dict:
    db = dict(_MYTHS)
    if isinstance(config, dict) and isinstance(config.get("myths"), dict):
        for k, v in config["myths"].items():
            if str(v).strip():
                db[str(k)] = str(v).strip()
    return db


def myths(config=None) -> list:
    return list(_table(config))


def find_myth(query, config=None) -> str:
    u = str(query or "")
    db = _table(config)
    best, blen = "", 0
    for name in db:
        if name in u and len(name) > blen:
            best, blen = name, len(name)
    for a, real in _ALIAS.items():
        if a in u and len(a) > blen and real in db:
            best, blen = real, len(a)
    return best


def about(query, config=None) -> str:
    db = _table(config)
    name = query if query in db else find_myth(query, config)
    s = db.get(name)
    return f"{name}：{s}" if s else ""


def is_myth_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("神话", "神话传说", "民间传说", "上古传说")):
        return True
    if find_myth(u, config) and any(k in u for k in ("的故事", "是什么", "讲讲", "怎么回事",
                                                     "传说", "什么意思", "讲一个", "啥故事")):
        return True
    return False

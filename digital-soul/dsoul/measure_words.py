"""量词：一‘条’鱼、一‘匹’马、一‘头’牛——中文的量词最讲究，教孩子说对。
"鱼用什么量词""一什么马"，查一查就清楚。纯数据 + 纯逻辑、可单测。可在 config 加。
"""

from __future__ import annotations

# 名词 → (量词, 例子)
_MEASURES = {
    "鱼": ("条", "一条鱼"), "马": ("匹", "一匹马"), "牛": ("头", "一头牛"),
    "羊": ("只", "一只羊"), "猪": ("头", "一头猪"), "狗": ("只", "一只狗"),
    "猫": ("只", "一只猫"), "鸟": ("只", "一只鸟"), "鸡": ("只", "一只鸡"),
    "象": ("头", "一头大象"), "骆驼": ("峰", "一峰骆驼"), "狼": ("只", "一只狼"),
    "纸": ("张", "一张纸"), "笔": ("支", "一支笔"), "书": ("本", "一本书"),
    "花": ("朵", "一朵花"), "树": ("棵", "一棵树"), "草": ("棵", "一棵草"),
    "山": ("座", "一座山"), "桥": ("座", "一座桥"), "楼": ("座", "一座楼"),
    "河": ("条", "一条河"), "路": ("条", "一条路"), "船": ("艘", "一艘船（小船用‘条’）"),
    "车": ("辆", "一辆车"), "飞机": ("架", "一架飞机"), "衣服": ("件", "一件衣服"),
    "裤子": ("条", "一条裤子"), "房子": ("间", "一间房（整栋用‘栋/座’）"),
    "灯": ("盏", "一盏灯"), "伞": ("把", "一把伞"), "刀": ("把", "一把刀"),
    "椅子": ("把", "一把椅子"), "信": ("封", "一封信"), "画": ("幅", "一幅画"),
    "布": ("匹", "一匹布"), "牙": ("颗", "一颗牙"), "星": ("颗", "一颗星"),
    "米": ("粒", "一粒米"), "云": ("朵", "一朵云"), "马路": ("条", "一条马路"),
    "蛇": ("条", "一条蛇"), "龙": ("条", "一条龙"), "笑话": ("个", "一个笑话"),
    "歌": ("首", "一首歌"), "诗": ("首", "一首诗"), "枪": ("把", "一把枪"),
    "镜子": ("面", "一面镜子"), "旗": ("面", "一面旗"), "鼓": ("面", "一面鼓"),
}

_ALIAS = {"大象": "象", "小狗": "狗", "小猫": "猫", "小鸟": "鸟", "毛笔": "笔"}


def _table(config) -> dict:
    db = dict(_MEASURES)
    if isinstance(config, dict) and isinstance(config.get("measure_words"), dict):
        for k, v in config["measure_words"].items():
            if isinstance(v, (list, tuple)) and v:
                db[str(k)] = (str(v[0]), str(v[1]) if len(v) > 1 else f"一{v[0]}{k}")
            elif isinstance(v, str) and v.strip():
                db[str(k)] = (v.strip(), f"一{v.strip()}{k}")
    return db


def find_noun(query, config=None) -> str:
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


def measure_of(query, config=None) -> str:
    """这个东西用什么量词。认不出返回空。"""
    db = _table(config)
    name = query if query in db else find_noun(query, config)
    row = db.get(name)
    if not row:
        return ""
    liang, example = row
    return f"{name}用量词「{liang}」，{example}。"


def is_measure_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if not find_noun(u, config):
        return False
    return any(k in u for k in ("量词", "一什么", "用什么量", "怎么数", "一个还是一只",
                                "该用什么", "用哪个量"))

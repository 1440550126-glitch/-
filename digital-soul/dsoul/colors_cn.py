"""中国传统色：月白、黛、胭脂、天青……老祖宗给颜色起的名字，又雅又美。
"天青是什么颜色""黛色是啥"，说出个门道，听着就有意境。

纯数据 + 纯逻辑、可单测。可在 config 加。
"""

from __future__ import annotations

_COLORS = {
    "月白": "极淡的蓝白色，像清冷的月光，素净。",
    "天青": "雨过天晴后的淡蓝色，宋代汝窑名色，‘雨过天青云破处’。",
    "黛": "青黑色，古代女子用来画眉，‘眉黛’说的就是它。",
    "胭脂": "红中带紫的浓红，女子化妆点唇抹腮的颜色。",
    "藕荷": "浅浅的紫里透粉，像莲藕断面的淡色，温柔。",
    "朱红": "鲜艳正气的红，宫墙、印泥、朱漆都是这个红。",
    "绛紫": "暗红发紫，深沉庄重。",
    "黛绿": "墨绿里带点青，深而沉静，远山的颜色。",
    "竹青": "竹子那种青翠带黄的绿，清新。",
    "黛蓝": "深沉的蓝，像暮色里的远山。",
    "靛青": "深蓝色，‘青出于蓝而胜于蓝’的那个青，来自蓝草。",
    "石青": "国画里的蓝绿色矿物颜料，沉稳。",
    "鹅黄": "嫩嫩的浅黄，像刚出壳的小鹅、初春的柳芽。",
    "明黄": "明亮的正黄，从前是皇家专用的尊贵颜色。",
    "缃色": "浅黄色，古书书衣常用。",
    "妃色": "粉红偏艳的颜色，又叫杨妃色。",
    "海棠红": "娇艳的粉红，像海棠花。",
    "缥色": "淡淡的青白色，‘缥缈’的缥。",
    "苍色": "灰中带青，‘苍天’‘苍山’的那种深远。",
    "秋香": "绿中带黄的颜色，沉静雅致，像深秋的草木。",
    "黧": "黑中带黄，‘面黧黑’说的是这色。",
    "黝": "青黑色，又黑又亮。",
}

_ALIAS = {"眉黛": "黛", "天青色": "天青", "月白色": "月白", "靛蓝": "靛青", "鹅黄色": "鹅黄"}


def _table(config) -> dict:
    db = dict(_COLORS)
    if isinstance(config, dict) and isinstance(config.get("colors"), dict):
        for k, v in config["colors"].items():
            if str(v).strip():
                db[str(k)] = str(v).strip()
    return db


def colors(config=None) -> list:
    return list(_table(config))


def find_color(query, config=None) -> str:
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
    name = query if query in db else find_color(query, config)
    s = db.get(name)
    return f"{name}：{s}" if s else ""


def is_color_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("传统色", "中国色", "古代颜色")):
        return True
    if find_color(u, config) and any(k in u for k in ("什么颜色", "是啥颜色", "是什么色",
                                                      "什么色", "是啥", "什么意思", "啥颜色",
                                                      "是哪种")):
        return True
    return False

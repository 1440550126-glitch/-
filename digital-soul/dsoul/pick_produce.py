"""挑食材：买菜买水果怎么挑才新鲜划算——拍西瓜、掂橙子、看鱼眼。
菜市场里的老经验，省得买回家不甜不新鲜。像个会买菜的人，搭把手。

纯数据 + 纯逻辑、可单测。可在 config 加自家的挑选窍门。
"""

from __future__ import annotations

_PICK = {
    "西瓜": "瓜脐和瓜蒂都凹进去的、瓜藤卷曲的熟；拍一拍‘咚咚’脆响的甜，‘噗噗’发闷的过了。",
    "橙子": "拿手里沉甸甸的水分足、皮薄光滑、肚脐小的甜。",
    "苹果": "红里透黄、麻点多的甜，掂着压手的水分足。",
    "西红柿": "自然熟的蒂周围微微泛青转红、圆润不带尖；别挑太红发软的（多是催熟）。",
    "菠萝": "闻着香、外皮转黄、轻按略有弹性的好；硬邦邦没香味的没熟，太软的过了。",
    "葡萄": "果皮上白霜（果粉）多的新鲜，提起一串不掉粒的好。",
    "香蕉": "黄里带点麻点的最甜，青的买回放两天再吃。",
    "桃子": "闻着香、绒毛自然、捏着不硬不烂的刚好。",
    "鸡蛋": "表面粗糙发涩的新鲜、摇一摇不晃荡的好、放水里沉底的新鲜。",
    "鱼": "眼睛清亮鼓、鱼鳃鲜红、按一按肉有弹性、不腥臭的新鲜。",
    "虾": "头和身子紧连不脱、壳发亮、肉紧实有弹性的新鲜。",
    "螃蟹": "掂着沉、壳硬、肚脐鼓（膏黄满）、腿脚有力会动的好。",
    "白菜": "包得紧实、掂着沉、根部白净没烂的好。",
    "萝卜": "掂着沉、表皮光滑无须根；太轻的可能糠心空了。",
    "土豆": "硬实、表皮干爽、没发芽没发青（发青发芽的别吃）。",
    "黄瓜": "顶花带刺、细直、捏着硬挺的新鲜。",
    "排骨": "颜色淡红有光泽、按一下能回弹、闻着没异味、不黏手的新鲜。",
    "猪肉": "淡红有光泽、肥肉洁白、按压回弹、不黏手的新鲜。",
    "玉米": "外皮翠绿、须发深、剥开颗粒饱满整齐的好。",
    "豆腐": "颜色微黄不发暗、闻着豆香没酸味、表面不黏的新鲜。",
}

_ALIAS = {"瓜": "西瓜", "番茄": "西红柿", "提子": "葡萄", "马铃薯": "土豆", "洋芋": "土豆",
          "大白菜": "白菜", "胡萝卜": "萝卜", "白萝卜": "萝卜", "活鱼": "鱼"}


def _table(config) -> dict:
    db = dict(_PICK)
    if isinstance(config, dict) and isinstance(config.get("pick_produce"), dict):
        for k, v in config["pick_produce"].items():
            if str(v).strip():
                db[str(k)] = str(v).strip()
    return db


def items(config=None) -> list:
    return list(_table(config))


def find_item(query, config=None) -> str:
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


def tip_for(query, config=None) -> str:
    db = _table(config)
    name = query if query in db else find_item(query, config)
    tip = db.get(name)
    return f"挑{name}：{tip}" if tip else ""


def is_pick_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if not find_item(u, config):
        return False
    return any(k in u for k in ("怎么挑", "咋挑", "怎么选", "挑选", "怎么买", "挑个", "选个",
                                "怎么看新鲜", "新鲜不"))

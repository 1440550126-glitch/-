"""绕口令：练嘴皮子、逗孩子乐——"吃葡萄不吐葡萄皮""四是四，十是十"。
跟语音一脉相承：说得溜不溜，绕口令最考人。纯数据 + 纯逻辑、可单测。

可在 config 里加自家的；按难度挑，也能按词找那条（"葡萄那个怎么说"）。
"""

from __future__ import annotations

# (题目, 难度1-3, 关键词)
_TWISTERS = [
    ("吃葡萄不吐葡萄皮，不吃葡萄倒吐葡萄皮。", 1, ["葡萄", "皮"]),
    ("四是四，十是十，十四是十四，四十是四十。", 1, ["四", "十", "数"]),
    ("红凤凰，黄凤凰，粉红凤凰花凤凰。", 2, ["凤凰", "红", "黄"]),
    ("板凳宽，扁担长，扁担绑在板凳上。", 2, ["板凳", "扁担"]),
    ("八百标兵奔北坡，炮兵并排北边跑。", 3, ["标兵", "炮兵", "兵"]),
    ("黑化肥发灰，灰化肥发黑。", 3, ["化肥", "黑", "灰"]),
    ("门口挂盏灯，灯下蹲着一只猫。", 1, ["灯", "猫"]),
    ("天上一颗星，地上一块冰，屋里一盏灯，墙上一根钉。", 2, ["星", "冰", "灯", "钉"]),
    ("牛郎恋刘娘，刘娘念牛郎。", 2, ["牛郎", "刘娘"]),
    ("妈妈骑马，马慢，妈妈骂马。", 1, ["妈", "马"]),
    ("白石塔，白石搭，白石搭白塔，白塔白石搭。", 3, ["白石", "塔"]),
    ("出南门走六步，见着六叔和六舅。", 2, ["六", "叔", "舅"]),
    ("四是四，十是十，十四是十四，四十是四十，谁把十四说成四十就打四十。", 3, ["四", "十"]),
    ("扁担长，板凳宽，板凳没有扁担长，扁担没有板凳宽。", 2, ["扁担", "板凳"]),
    ("打南边来了个哑巴，腰里别了个喇叭。", 3, ["哑巴", "喇叭"]),
    ("一面小花鼓，鼓上画老虎，宝宝敲破鼓，拿布来补鼓。", 3, ["鼓", "虎", "布"]),
    ("化肥会挥发，黑化肥发灰会挥发，灰化肥挥发会发黑。", 3, ["化肥", "挥发"]),
    ("吃枣子，吐枣核儿；吃葡萄，吐葡萄皮儿。", 2, ["枣", "葡萄"]),
    ("红鲤鱼，绿鲤鱼，与驴。", 3, ["鲤鱼", "驴"]),
    ("三月三，小三去登山；山高路又陡，小三流了汗。", 2, ["三", "山"]),
    ("墙上一根钉，钉上挂条绳，绳头打个洞，洞里穿根针。", 2, ["钉", "绳", "针"]),
    ("会炖我的炖冻豆腐，来炖我的炖冻豆腐。", 3, ["炖", "豆腐"]),
    ("七巷一个漆匠，西巷一个锡匠；漆匠拿锡，锡匠拿漆。", 3, ["漆匠", "锡匠"]),
    ("石狮寺前有四十四个石狮子。", 3, ["石狮", "石狮子"]),
]


def _all(config=None) -> list:
    items = list(_TWISTERS)
    if isinstance(config, dict) and isinstance(config.get("tongue_twisters"), list):
        for t in config["tongue_twisters"]:
            if isinstance(t, str) and t.strip():
                items.append((t.strip(), 2, []))
            elif isinstance(t, dict) and t.get("text"):
                items.append((t["text"].strip(), int(t.get("level", 2)), t.get("keys", [])))
    return items


def all_twisters(config=None) -> list:
    return [t[0] for t in _all(config)]


def count(config=None) -> int:
    return len(_all(config))


def random_one(seed="", config=None) -> str:
    items = _all(config)
    return items[len(str(seed)) % len(items)][0] if items else ""


def by_keyword(query, config=None) -> str:
    """按词找那条绕口令（"葡萄那个"→吃葡萄…）。找不到返回空。"""
    u = str(query or "")
    if not u:
        return ""
    for text, _lv, keys in _all(config):
        if any(k and k in u for k in keys):
            return text
    return ""


def by_level(level, seed="", config=None) -> str:
    """挑某个难度的一条（1 易 3 难）。该难度没有就随便来一条。"""
    pool = [t for t in _all(config) if t[1] == int(level)]
    if not pool:
        return random_one(seed, config)
    return pool[len(str(seed)) % len(pool)][0]


def is_twister_request(utterance) -> bool:
    u = str(utterance or "")
    return any(k in u for k in ("绕口令", "练练嘴", "练嘴皮", "顺口溜练", "考考嘴"))


def wants_hard(utterance) -> bool:
    u = str(utterance or "")
    return any(k in u for k in ("难", "高级", "厉害", "来个狠", "上难度"))

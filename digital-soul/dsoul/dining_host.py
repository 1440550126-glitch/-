"""点菜请客帮手：几个人点几个菜、荤素冷热怎么搭、敬酒买单怎么得体——
长辈张罗一桌饭，面子里子都想周到。这一块出出主意，不露怯、不浪费。纯逻辑、可单测。
和"人情礼俗"(etiquette)、"菜系"(cuisines)接着用，这里管"怎么点、怎么待客"。
"""

from __future__ import annotations

# 主题 -> (怎么做, 提醒)
_TOPICS = {
    "点几个菜": ("一般按'人数 + 1~2 道'点：人多再加两个;讲究点的凑双数吉利。"
              "宁可不够再加，也别一上来点一堆吃不完、浪费还心疼。",
              "拿不准告诉我几位客人，我替你算个数。"),
    "荤素搭配": ("荤素大致一半一半、再来个豆制品和时蔬;别全是大鱼大肉，老人小孩也照顾到;"
              "口味别全是辣的/全是甜的，搭开。",
              "问一句有没有忌口（不吃辣、海鲜过敏、清真、吃素），最显周到。"),
    "上菜顺序": ("通常先上凉菜垫垫、再热炒、然后硬菜大菜、跟个汤、配主食（米饭/面点），最后果盘收尾。",
              "凉菜先到能让客人先动筷，别冷场。"),
    "点菜搭配": ("一桌讲究'有凉有热、有荤有素、有干有汤、有一道撑场面的硬菜';"
              "再来道主食垫底、别让人只喝酒不吃饭。",
              "点一两道招牌特色，主人脸上有光、客人也尝鲜。"),
    "敬酒": ("主人先起身敬一圈、长辈贵客优先;晚辈给长辈敬酒，杯子端低一点表示尊敬;"
           "说句吉利话再喝;能喝多少量力，不强劝酒。",
           "不喝酒以茶代酒也行，心意到了就好。"),
    "买单结账": ("做东的提前或悄悄去把账结了最体面，别当众抢得面红耳赤;"
              "实在要 AA 就饭前说清楚，免得尴尬。",
              "请客图的是高兴，别在钱上较劲伤了和气。"),
    "在家待客": ("菜量备足点、宁多勿少;长辈、贵客让上座（一般正对门或里侧）;"
              "茶水续上、热情张罗;有忌口的提前问、单独备一份。",
              "家常菜用心做，比山珍海味更暖人。"),
}

_ALIAS = {
    "点几个菜": "点几个菜", "点几个": "点几个菜", "点多少菜": "点几个菜", "几个菜合适": "点几个菜",
    "荤素搭配": "荤素搭配", "荤素": "荤素搭配", "怎么搭配": "荤素搭配", "忌口": "荤素搭配",
    "上菜顺序": "上菜顺序", "上菜": "上菜顺序", "先上什么": "上菜顺序",
    "点菜搭配": "点菜搭配", "怎么点菜": "点菜搭配", "点菜": "点菜搭配", "点一桌": "点菜搭配",
    "敬酒": "敬酒", "敬酒词": "敬酒", "怎么敬酒": "敬酒", "劝酒": "敬酒",
    "买单结账": "买单结账", "买单": "买单结账", "结账": "买单结账", "谁付钱": "买单结账", "AA": "买单结账",
    "在家待客": "在家待客", "待客": "在家待客", "请客在家": "在家待客", "客人来家": "在家待客", "招待客人": "在家待客",
}


def _all(config=None) -> dict:
    d = dict(_TOPICS)
    cfg = (config or {}).get("dining_host") if isinstance(config, dict) else None
    extra = (cfg or {}).get("topics") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("how"):
                d[str(name)] = (str(v["how"]), str(v.get("tip", "")))
    return d


def topics(config=None) -> list:
    return list(_all(config).keys())


def find_topic(utterance, config=None):
    """认出问的哪类点菜/宴请（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def advice(topic, config=None) -> str:
    """某类的做法 + 提醒。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(topic or ""), str(topic or ""))
    if key not in d:
        return ""
    how, tip = d[key]
    return f"{key}：{how}" + (f"（{tip}）" if tip else "")


def suggest_dish_count(people) -> str:
    """按人数估个点菜数（荤素搭配建议）。"""
    try:
        n = int(people)
    except (TypeError, ValueError):
        return ""
    if n <= 0:
        return ""
    low, high = n, n + 2
    veg = max(1, high // 2)
    return (f"{n} 位的话，点 {low}～{high} 道菜比较稳：荤菜 {high - veg} 道左右、"
            f"素菜 {veg} 道，再加 1 个汤和主食。先问问有没有忌口。宁可不够再加，别浪费。")


def is_dining_query(utterance, config=None) -> bool:
    """是不是在问点菜/请客的事。"""
    u = str(utterance or "")
    if any(k in u for k in ("点菜", "点几个菜", "点一桌", "请客", "宴请", "招待客人", "待客")):
        return True
    if find_topic(u, config) and any(k in u for k in ("怎么", "咋", "搭配", "顺序", "得体",
                                                      "合适", "讲究", "注意", "怎么办")):
        return True
    return False


def count(config=None) -> int:
    return len(_all(config))

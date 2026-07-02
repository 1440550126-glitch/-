"""祝福语 / 贺词：到了场面上要说句吉利话，张口就来——生日、结婚、乔迁、寿宴、
升学、满月、开业、康复、退休、拜年。帮老人（和嘴笨的我们）体面地把心意说出口。

每个场合备几句、轮换着来。纯数据 + 纯逻辑、可单测。可在 config 加自家的。
"""

from __future__ import annotations

_BLESSINGS = {
    "生日": [
        "生日快乐！愿你身体健康、事事顺心，笑口常开。",
        "祝你生日快乐，岁岁平安，年年有今朝！",
        "又长一岁，愿你所求皆如愿，所行皆坦途。生日快乐！",
    ],
    "寿宴": [
        "福如东海长流水，寿比南山不老松！祝老寿星健康长寿。",
        "寿星公/寿星婆，祝您福寿安康、儿孙满堂、笑享天年！",
    ],
    "结婚": [
        "百年好合，永结同心！愿你们相敬如宾，白头偕老。",
        "新婚快乐！愿你们恩恩爱爱、和和美美，早生贵子。",
        "天作之合，佳偶天成！祝新人甜甜蜜蜜，幸福一生。",
    ],
    "乔迁": [
        "乔迁新居，吉祥如意！愿新家温暖、阖家幸福安康。",
        "恭贺乔迁之喜！新居纳福，日子越过越红火。",
    ],
    "升学": [
        "金榜题名，前程似锦！愿你学业有成、鹏程万里。",
        "恭喜金榜题名！愿你在新天地里，乘风破浪、大展宏图。",
    ],
    "满月": [
        "宝宝满月，健康快乐！愿小家伙茁壮成长，全家欢喜。",
        "恭喜喜得贵子/千金！祝宝宝聪明伶俐、平安长大。",
    ],
    "开业": [
        "开业大吉，生意兴隆！财源广进，宾客盈门。",
        "恭贺开业！愿生意红红火火，越做越大。",
    ],
    "康复": [
        "愿你早日康复，身体安康！别急，慢慢养，会好起来的。",
        "祝你药到病除、早日痊愈，往后健健康康。",
    ],
    "退休": [
        "退休快乐！忙了大半辈子，往后含饴弄孙、安享清福。",
        "恭祝荣休！愿你生活惬意、身体硬朗，日子越过越舒坦。",
    ],
    "拜年": [
        "新年好！恭喜发财，万事如意，身体健康！",
        "给您拜年啦！祝您新春大吉、阖家幸福、岁岁平安。",
        "新的一年，愿你顺顺利利、红红火火、心想事成！",
    ],
    "升职": [
        "恭喜高升！愿你步步高升、前程似锦。",
        "贺你荣升！再接再厉，鹏程万里。",
    ],
}

_ALIAS = {
    "过年": "拜年", "新年": "拜年", "春节": "拜年", "拜年话": "拜年",
    "大寿": "寿宴", "祝寿": "寿宴", "寿辰": "寿宴",
    "新婚": "结婚", "婚礼": "结婚", "成婚": "结婚",
    "搬家": "乔迁", "新居": "乔迁", "入伙": "乔迁",
    "金榜": "升学", "考上": "升学", "升学宴": "升学",
    "孩子满月": "满月", "弥月": "满月",
    "开张": "开业", "开店": "开业",
    "病好": "康复", "出院": "康复", "痊愈": "康复",
    "荣休": "退休",
    "高升": "升职", "升迁": "升职",
}


def occasions() -> list:
    return list(_BLESSINGS.keys())


def _table(config) -> dict:
    db = {k: list(v) for k, v in _BLESSINGS.items()}
    if isinstance(config, dict) and isinstance(config.get("blessings"), dict):
        for k, v in config["blessings"].items():
            lines = [v] if isinstance(v, str) else list(v or [])
            lines = [str(x).strip() for x in lines if str(x).strip()]
            if lines:
                db[k] = lines + db.get(k, [])
    return db


def normalize_occasion(name) -> str:
    n = str(name or "").strip()
    if n in _BLESSINGS:
        return n
    for k, v in _ALIAS.items():
        if k in n:
            return v
    for k in _BLESSINGS:
        if k in n:
            return k
    return ""


def detect_occasion(utterance, config=None) -> str:
    u = str(utterance or "")
    if not u:
        return ""
    db = _table(config)                            # 含配置新增的场合
    keys = list(db) + list(_ALIAS)
    best, blen = "", 0
    for k in keys:
        if k in u and len(k) > blen:
            best, blen = k, len(k)
    if not best:
        return ""
    return best if best in db else normalize_occasion(best)


def bless_for(occasion, seed="", config=None) -> str:
    """给这个场合一句祝福语（轮换）。认不出场合返回空。"""
    db = _table(config)
    occ = occasion if occasion in db else normalize_occasion(occasion)
    pool = db.get(occ, [])
    if not pool:
        return ""
    return pool[len(str(seed)) % len(pool)]


def is_blessing_request(utterance) -> bool:
    u = str(utterance or "")
    return any(k in u for k in ("祝福语", "贺词", "吉利话", "拜年话", "说句祝福",
                                "怎么祝福", "写句祝福", "祝酒词", "送句祝福", "祝福的话",
                                "说点吉利", "讨个口彩"))

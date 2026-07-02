"""八大菜系：川鲁粤苏闽浙湘徽，各是什么口味、有哪些名菜。
聊吃的，中国人最有话说。纯数据 + 纯逻辑、可单测。可在 config 加。
"""

from __future__ import annotations

_CUISINES = {
    "鲁菜": ("山东菜，八大菜系之首", "咸鲜为主、讲究火候，善用葱姜", "糖醋鲤鱼、九转大肠、葱烧海参"),
    "川菜": ("四川菜", "麻辣鲜香、一菜一格、百菜百味", "麻婆豆腐、回锅肉、水煮鱼、宫保鸡丁"),
    "粤菜": ("广东菜", "清淡鲜美、讲究本味，会煲汤", "白切鸡、烧鹅、清蒸鱼、广式早茶"),
    "苏菜": ("江苏菜", "清淡精致、刀工细腻、注重原汁", "松鼠桂鱼、清炖蟹粉狮子头、盐水鸭"),
    "闽菜": ("福建菜", "鲜醇清爽、善用海鲜、汤菜见长", "佛跳墙、荔枝肉、醉糟鸡"),
    "浙菜": ("浙江菜", "清香爽脆、鲜嫩软滑", "西湖醋鱼、东坡肉、龙井虾仁、宋嫂鱼羹"),
    "湘菜": ("湖南菜", "香辣酸辣、油重色浓", "剁椒鱼头、辣椒炒肉、毛氏红烧肉、口味虾"),
    "徽菜": ("安徽菜", "重油重色、擅长烧炖、讲究火功", "臭鳜鱼、毛豆腐、火腿炖甲鱼"),
}

_ALIAS = {"山东菜": "鲁菜", "四川菜": "川菜", "广东菜": "粤菜", "江苏菜": "苏菜",
          "福建菜": "闽菜", "浙江菜": "浙菜", "湖南菜": "湘菜", "安徽菜": "徽菜"}


def _table(config) -> dict:
    db = dict(_CUISINES)
    if isinstance(config, dict) and isinstance(config.get("cuisines"), dict):
        for k, v in config["cuisines"].items():
            if isinstance(v, (list, tuple)) and len(v) >= 3:
                db[str(k)] = (str(v[0]), str(v[1]), str(v[2]))
    return db


def cuisines(config=None) -> list:
    return list(_table(config))


def eight_cuisines() -> str:
    return "八大菜系是：鲁、川、粤、苏、闽、浙、湘、徽。"


def find_cuisine(query, config=None) -> str:
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
    name = query if query in db else find_cuisine(query, config)
    row = db.get(name)
    if not row:
        return ""
    where, taste, dishes = row
    return f"{name}（{where}）：{taste}。名菜有{dishes}。"


def is_cuisine_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("八大菜系", "菜系")):
        return True
    if find_cuisine(u, config) and any(k in u for k in ("是什么", "特点", "名菜", "有什么菜",
                                                        "口味", "介绍", "讲讲", "怎么样")):
        return True
    return False

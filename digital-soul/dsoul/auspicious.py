"""吉祥寓意：年画窗花上为啥总画蝙蝠、鱼、葫芦——藏着谐音和好彩头。
"鱼是什么寓意""为什么贴蝙蝠"，说出门道，过年的讲究就明白了。

纯数据 + 纯逻辑、可单测。可在 config 加。
"""

from __future__ import annotations

_SYMBOLS = {
    "蝙蝠": "‘蝠’谐音‘福’，画五只蝙蝠就是‘五福临门’。",
    "鱼": "‘鱼’谐音‘余’，年年有‘鱼’就是‘年年有余’，年夜饭的鱼要留一点。",
    "葫芦": "‘葫芦’谐音‘福禄’，藤蔓绵延又寓意子孙昌盛。",
    "鹿": "‘鹿’谐音‘禄’，象征福禄、官运财运。",
    "桃": "寿桃，象征长寿，祝寿离不开它。",
    "石榴": "籽多，寓意‘多子多福’。",
    "喜鹊": "‘喜’鸟，两只喜鹊是‘双喜’，喜鹊登梅是‘喜上眉梢’。",
    "鸳鸯": "成双成对，象征夫妻恩爱、白头偕老。",
    "牡丹": "花中之王，象征富贵荣华，‘富贵牡丹’。",
    "莲": "‘莲’谐音‘连’，连年有余；出淤泥而不染，又象征清廉。",
    "竹": "‘竹’寓意节节高升、虚心有节。",
    "松鹤": "松与鹤都长寿，‘松鹤延年’祝老人健康长寿。",
    "龙凤": "龙凤呈祥，象征吉祥喜庆，婚礼上‘龙凤配’。",
    "麒麟": "瑞兽，‘麒麟送子’寓意求得贵子。",
    "如意": "称心如意，‘事事如意’，玉如意是吉祥摆件。",
    "元宝": "象征招财进宝、财源广进。",
    "柿子": "‘柿’谐音‘事’，柿子配如意是‘事事如意’。",
    "花生": "又叫长生果，寓意长生、多子（‘花’着生男生女）。",
    "牡丹凤凰": "‘凤穿牡丹’，富贵吉祥。",
    "蝴蝶": "‘蝶’谐音‘耋’，与猫（耄）一起寓意长寿；也象征美好爱情。",
    "枣": "‘枣’谐音‘早’，枣与栗子是‘早立子’，桂圆莲子枣是‘早生贵子’。",
    "羊": "‘羊’通‘祥’，‘三羊开泰’是吉利话。",
    "葫芦藤": "藤蔓绵长，寓意子孙万代、福禄绵延。",
}

_ALIAS = {"福鱼": "鱼", "寿桃": "桃", "莲花": "莲", "荷花": "莲", "竹子": "竹",
          "凤凰": "龙凤", "龙": "龙凤", "大象": "如意"}


def _table(config) -> dict:
    db = dict(_SYMBOLS)
    if isinstance(config, dict) and isinstance(config.get("auspicious"), dict):
        for k, v in config["auspicious"].items():
            if str(v).strip():
                db[str(k)] = str(v).strip()
    return db


def symbols(config=None) -> list:
    return list(_table(config))


def find_symbol(query, config=None) -> str:
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


def meaning_of(query, config=None) -> str:
    db = _table(config)
    name = query if query in db else find_symbol(query, config)
    s = db.get(name)
    return f"{name}：{s}" if s else ""


def is_auspicious_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("吉祥寓意", "吉祥图案", "吉祥话", "好彩头", "什么彩头")):
        return True
    if find_symbol(u, config) and any(k in u for k in ("寓意", "象征", "什么意思", "为什么贴",
                                                       "为什么画", "代表什么", "啥意思", "讲究")):
        return True
    return False

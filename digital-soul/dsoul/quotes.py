"""名言金句：肚里存一摞名人名言、格言警句——勉励晚辈、点拨人心、写贺卡都用得上。
跟"俗语谚语"(proverbs)、"本人口头语录"(sayings)不一样：这些是有出处、有作者的名句。
按主题挑一句应景的，或问"关于坚持的名言"就给几句。纯数据 + 纯逻辑、可单测。

出处尽量取公认的经典（论语/孟子/荀子/老子，及杜甫/李白/陆游/范仲淹/文天祥/诸葛亮等），
拿不准的不硬安作者，宁可标"古语/贤文"。
"""

from __future__ import annotations

# 主题 -> [(名句, 出处)]
_QUOTES = {
    "读书治学": [
        ("学而不思则罔，思而不学则殆。", "《论语》"),
        ("读书破万卷，下笔如有神。", "杜甫"),
        ("纸上得来终觉浅，绝知此事要躬行。", "陆游"),
        ("三人行，必有我师焉。", "《论语》"),
        ("敏而好学，不耻下问。", "《论语》"),
    ],
    "勤奋": [
        ("业精于勤，荒于嬉；行成于思，毁于随。", "韩愈"),
        ("宝剑锋从磨砺出，梅花香自苦寒来。", "《警世贤文》"),
        ("天行健，君子以自强不息。", "《周易》"),
        ("书山有路勤为径，学海无涯苦作舟。", "古语"),
    ],
    "坚持": [
        ("锲而不舍，金石可镂。", "荀子"),
        ("千里之行，始于足下。", "老子"),
        ("不积跬步，无以至千里；不积小流，无以成江海。", "荀子"),
        ("绳锯木断，水滴石穿。", "古语"),
    ],
    "立志": [
        ("有志者，事竟成。", "《后汉书》"),
        ("老当益壮，宁移白首之心；穷且益坚，不坠青云之志。", "王勃"),
        ("会当凌绝顶，一览众山小。", "杜甫"),
        ("长风破浪会有时，直挂云帆济沧海。", "李白"),
    ],
    "诚信品德": [
        ("人而无信，不知其可也。", "《论语》"),
        ("君子坦荡荡，小人长戚戚。", "《论语》"),
        ("勿以恶小而为之，勿以善小而不为。", "刘备"),
        ("君子成人之美，不成人之恶。", "《论语》"),
    ],
    "惜时": [
        ("一寸光阴一寸金，寸金难买寸光阴。", "《增广贤文》"),
        ("少壮不努力，老大徒伤悲。", "《长歌行》"),
        ("黑发不知勤学早，白首方悔读书迟。", "古语"),
    ],
    "逆境": [
        ("天将降大任于斯人也，必先苦其心志，劳其筋骨。", "《孟子》"),
        ("沉舟侧畔千帆过，病树前头万木春。", "刘禹锡"),
        ("山重水复疑无路，柳暗花明又一村。", "陆游"),
    ],
    "友谊": [
        ("海内存知己，天涯若比邻。", "王勃"),
        ("桃花潭水深千尺，不及汪伦送我情。", "李白"),
        ("莫愁前路无知己，天下谁人不识君。", "高适"),
    ],
    "家国": [
        ("先天下之忧而忧，后天下之乐而乐。", "范仲淹"),
        ("人生自古谁无死，留取丹心照汗青。", "文天祥"),
        ("位卑未敢忘忧国。", "陆游"),
    ],
    "修身": [
        ("己所不欲，勿施于人。", "《论语》"),
        ("静以修身，俭以养德；非淡泊无以明志，非宁静无以致远。", "诸葛亮"),
        ("吾日三省吾身。", "《论语》"),
        ("不以物喜，不以己悲。", "范仲淹"),
    ],
    "亲情": [
        ("谁言寸草心，报得三春晖。", "孟郊"),
        ("树欲静而风不止，子欲养而亲不待。", "《孔子家语》"),
    ],
}

# 口语主题 -> 规范主题
_ALIAS = {
    "读书": "读书治学", "学习": "读书治学", "治学": "读书治学", "求学": "读书治学",
    "勤奋": "勤奋", "努力": "勤奋", "勤勉": "勤奋", "刻苦": "勤奋",
    "坚持": "坚持", "毅力": "坚持", "恒心": "坚持", "持之以恒": "坚持",
    "立志": "立志", "志向": "立志", "理想": "立志", "抱负": "立志", "励志": "立志",
    "诚信": "诚信品德", "品德": "诚信品德", "做人": "诚信品德", "诚实": "诚信品德",
    "惜时": "惜时", "时间": "惜时", "珍惜时间": "惜时", "光阴": "惜时",
    "逆境": "逆境", "挫折": "逆境", "困难": "逆境", "失意": "逆境", "低谷": "逆境",
    "友谊": "友谊", "朋友": "友谊", "友情": "友谊", "知己": "友谊",
    "家国": "家国", "爱国": "家国", "报国": "家国", "天下": "家国",
    "修身": "修身", "修养": "修身", "为人": "修身", "处世": "修身",
    "亲情": "亲情", "父母": "亲情", "孝顺": "亲情", "感恩": "亲情",
}


def _all(config=None) -> dict:
    d = {k: list(v) for k, v in _QUOTES.items()}
    cfg = (config or {}).get("quotes") if isinstance(config, dict) else None
    if isinstance(cfg, dict):
        for theme, lst in cfg.items():
            bucket = d.setdefault(str(theme), [])
            for q in (lst or []):
                if isinstance(q, (list, tuple)) and q:
                    bucket.append((str(q[0]), str(q[1]) if len(q) > 1 else "佚名"))
                elif isinstance(q, dict) and q.get("text"):
                    bucket.append((str(q["text"]), str(q.get("by", "佚名"))))
                elif isinstance(q, str) and q.strip():
                    bucket.append((q.strip(), "佚名"))
    return d


def themes(config=None) -> list:
    return list(_all(config).keys())


def find_theme(utterance, config=None):
    """从话里听出主题（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for theme in _all(config):
        if theme in u:
            return theme
    return None


def quotes_for(theme, config=None) -> list:
    cat = _ALIAS.get(str(theme or ""), str(theme or ""))
    return list(_all(config).get(cat, []))


def _fmt(q) -> str:
    text, by = q
    return f"「{text}」——{by}" if by else f"「{text}」"


def a_quote(theme=None, seed="", config=None) -> str:
    """来一句名言：给了主题就挑该主题的，否则跨主题挑一句。"""
    table = _all(config)
    if theme:
        pool = quotes_for(theme, config)
    else:
        pool = [q for lst in table.values() for q in lst]
    if not pool:
        pool = [q for lst in table.values() for q in lst]
    if not pool:
        return ""
    return _fmt(pool[len(str(seed)) % len(pool)])


def several(theme, n=3, seed="", config=None) -> str:
    """某主题来几句（写贺卡、给后辈勉励时用）。"""
    pool = quotes_for(theme, config)
    if not pool:
        return ""
    s = len(str(seed))
    picked = [pool[(s + i) % len(pool)] for i in range(min(max(1, int(n)), len(pool)))]
    return "；".join(_fmt(q) for q in picked) + "。"


def count(config=None) -> int:
    return sum(len(v) for v in _all(config).values())


def is_quote_query(utterance, config=None) -> bool:
    """是不是在求名言金句（要有名言类词；或"关于X的名言/句子"）。"""
    u = str(utterance or "")
    kind = any(k in u for k in ("名言", "名句", "金句", "格言", "警句", "座右铭", "至理名言"))
    if kind:
        return True
    # "关于坚持的句子/几句勉励的话" + 主题（场合类打气交给 encourage，这里要有明确主题词）
    if any(k in u for k in ("句子", "一句话", "励志的话", "几句", "勉励")) and find_theme(u, config):
        return True
    return False

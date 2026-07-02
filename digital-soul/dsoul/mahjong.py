"""麻将：陪长辈搓两圈、给晚辈讲讲规矩——术语、牌型、怎么算胡、常见番种。
麻将是中国人桌上的烟火气，老人最爱。这一块不赌钱，只讲门道：碰杠吃听胡是什么意思、
牌怎么分、几张才能胡、清一色碰碰胡这些大牌怎么来的。

纯数据 + 纯逻辑、可单测。讲规则、长见识、添乐子——小赌怡情也提醒一句别上头。
"""

from __future__ import annotations

# 术语 -> 通俗解释
_TERMS = {
    "碰": "别人打出的牌，正好和你手里两张一样，喊「碰」亮出来凑成三张（刻子）。",
    "杠": "四张一样的牌凑齐叫「杠」——明杠（碰了再摸到第四张）/暗杠（自己摸齐四张），杠完补一张再打。",
    "吃": "上家打出的牌，和你手里两张连成顺子（如二三万吃一万），喊「吃」。只能吃上家的。",
    "听": "「听牌」——只差一张就能胡了，就等那张牌（自摸或别人点）。",
    "胡": "凑齐和牌牌型（一般四副 + 一对将），叫「胡」，这把就赢了。",
    "自摸": "自己摸到那张胡牌，叫自摸；通常比别人点炮多算番。",
    "点炮": "你打出去的牌正好让别人胡了，叫点炮（放炮），这家由你赔。",
    "将": "胡牌里那一对相同的牌（也叫对子、雀头），是牌型的眼。",
    "刻子": "三张一模一样的牌（如三个五筒）。",
    "顺子": "同花色三张连号（如三、四、五条）。",
    "做庄": "当庄家，赢了多得、输了多赔；连赢叫连庄。",
    "流局": "牌摸光了谁也没胡，这把作废重来，叫流局（黄庄）。",
    "门清": "全程没碰没吃、自己摸成的，叫门前清，加番。",
    "报听": "提前声明听牌（有的玩法报听加番，但不能再换牌）。",
    "诈胡": "牌没成型却喊胡，叫诈胡，要受罚——看清楚再喊。",
}

# 牌的种类
_TILES = [
    ("万子", "一万到九万，共九种，写着「万」字。"),
    ("条子（索子）", "一条到九条，一条常画成一只鸟。"),
    ("筒子（饼子）", "一筒到九筒，圆圈像铜钱。"),
    ("风牌", "东、南、西、北四种方位风。"),
    ("箭牌", "中（红中）、发（发财）、白（白板）三种。"),
    ("花牌", "春夏秋冬、梅兰竹菊（有的玩法用，摸到补一张、加花）。"),
]

# 常见番种（牌型）-> 说明
_PATTERNS = [
    ("平胡", "最普通的胡牌：四副顺子/刻子 + 一对将，没什么特殊花样。"),
    ("碰碰胡", "全是刻子（三张一样的）加一对将，没有顺子——又叫对对胡。"),
    ("清一色", "整副牌全是同一种花色（全万、或全条、或全筒），大牌。"),
    ("混一色", "一种花色 + 字牌（风/箭）组成，比清一色稍小。"),
    ("七对", "七个对子凑成一手（特殊牌型，不用顺子刻子）。"),
    ("大三元", "中、发、白三种箭牌各凑一个刻子，超大番。"),
    ("小三元", "箭牌两个刻子 + 第三种箭牌作将。"),
    ("十三幺", "一万九万、一条九条、一筒九筒 + 东南西北中发白各一张，再凑一对，极罕见大牌。"),
    ("杠上开花", "开杠补牌时正好补到胡牌，喜上加喜，加番。"),
    ("海底捞月", "摸最后一张牌自摸胡，叫海底捞月。"),
]

_ALIAS = {
    "对对胡": "碰碰胡", "清一色牌": "清一色", "门前清": "门清", "黄庄": "流局",
    "放炮": "点炮", "雀头": "将", "对子": "将", "连庄": "做庄", "庄家": "做庄",
}


def terms(config=None) -> list:
    """所有术语名。"""
    return list(_merge_terms(config).keys())


def _merge_terms(config=None) -> dict:
    d = dict(_TERMS)
    cfg = (config or {}).get("mahjong") if isinstance(config, dict) else None
    extra = (cfg or {}).get("terms") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for k, v in extra.items():
            d[str(k)] = str(v)
    return d


def explain_term(name, config=None) -> str:
    """某个术语怎么讲。查不到返回空。"""
    d = _merge_terms(config)
    key = _ALIAS.get(str(name or ""), str(name or ""))
    return d.get(key, "")


def find_term(utterance, config=None) -> str:
    """从话里认出问的是哪个术语（最长匹配，含别名）。认不出返回空。"""
    u = str(utterance or "")
    cands = list(_merge_terms(config).keys()) + list(_ALIAS.keys())
    for name in sorted(set(cands), key=len, reverse=True):
        if name and name in u:
            return _ALIAS.get(name, name)
    return ""


def patterns(config=None) -> list:
    """常见番种 [(名, 说明)]。"""
    items = list(_PATTERNS)
    cfg = (config or {}).get("mahjong") if isinstance(config, dict) else None
    extra = (cfg or {}).get("patterns") if isinstance(cfg, dict) else None
    if isinstance(extra, list):
        for p in extra:
            if isinstance(p, (list, tuple)) and len(p) >= 2:
                items.append((str(p[0]), str(p[1])))
    return items


def find_pattern(utterance, config=None) -> str:
    """问某个番种怎么算（"清一色是啥"）。返回说明或空。"""
    u = str(utterance or "")
    for name, desc in patterns(config):
        if name in u:
            return f"{name}：{desc}"
    # 别名（对对胡→碰碰胡）
    for alias, real in _ALIAS.items():
        if alias in u:
            for name, desc in patterns(config):
                if name == real:
                    return f"{name}：{desc}"
    return ""


def tiles_intro() -> str:
    """麻将牌都有哪些。"""
    body = "；".join(f"{n}（{d}）" for n, d in _TILES)
    return "麻将牌分这几类：" + body + "。一副通常一百三十六张。"


def basics() -> str:
    """胡牌的基本规矩，一段话讲明白。"""
    return ("基本规矩：每人先摸十三张，轮流摸一张打一张。凑齐「四副 + 一对将」就能胡——"
            "一副是三张顺子（连号同花色）或刻子（三张一样），将是一对相同的牌。"
            "别人打的牌能用就喊碰/杠/吃，只差一张时叫听牌，等到那张就胡。"
            "自己摸到胡叫自摸，别人打的让你胡叫点炮。图个乐子，小赌怡情，别上头。")


def is_mahjong_query(utterance, config=None) -> bool:
    """是不是在聊麻将（有麻将相关词 + 问/学/教的意思，或直接点了术语/番种）。"""
    u = str(utterance or "")
    if "麻将" in u and any(k in u for k in ("怎么", "规则", "教", "学", "玩", "打", "什么", "讲", "番", "胡")):
        return True
    # 直接问术语/番种也算（"碰是什么意思""清一色怎么胡"）
    if find_term(u, config) and any(k in u for k in ("什么", "意思", "怎么", "啥", "讲讲", "规则")):
        return True
    if find_pattern(u, config) and any(k in u for k in ("什么", "意思", "怎么", "啥", "讲讲", "胡", "算")):
        return True
    return False


def count(config=None) -> int:
    """术语 + 番种 总条数（攒内容用）。"""
    return len(_merge_terms(config)) + len(patterns(config))

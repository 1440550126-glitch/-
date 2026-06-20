"""红包：发红包写句啥吉利话、包多少数字讨口彩——过年、结婚、生日、满月都用得上。
不替你定多少钱（量力而行最重要），只把"吉利数字的寓意"和"封面祝词"给你参考。
纯数据 + 纯逻辑、可单测。和 etiquette（送礼规矩）、blessings（一般祝福）各管一摊。
"""

from __future__ import annotations

# 吉利数字 -> 寓意（元）
_LUCKY = [
    (6, "六六大顺"), (66, "六六大顺"), (666, "六六大顺"), (6666, "顺顺顺"),
    (8, "发"), (88, "发发"), (888, "发发发"), (8888, "大发特发"),
    (168, "一路发"), (1688, "一路发"), (188, "一辈子发"), (1888, "一辈子发"),
    (520, "我爱你"), (521, "我愿意"), (1314, "一生一世"), (1213, "要爱一生"),
    (99, "长长久久"), (999, "长长久久"), (100, "圆圆满满"), (200, "成双成对"),
    (666.66, "顺到底"), (888.88, "发到底"),
]

# 场合 -> (封面/微信红包祝词们, 该场合更搭的吉利数, 忌讳提醒)
_OCCASIONS = {
    "压岁钱": (["岁岁平安，快快长大", "好好学习，天天向上", "新年快乐，红包拿好"],
              [100, 200, 500, 666, 800, 888], "图个双数吉利，别给单数。"),
    "拜年": (["新春大吉，万事如意", "恭喜发财，红包拿来", "龙马精神，步步高升"],
            [66, 88, 168, 666, 888], "走亲访友的小辈红包，双数为好。"),
    "婚礼": (["百年好合，永结同心", "新婚快乐，早生贵子", "白头偕老，幸福美满"],
            [666, 888, 999, 1314, 1666, 1888], "随礼图双数，888/1314 最讨喜；忌单数、忌带 4。"),
    "生日": (["生日快乐，岁岁平安", "福如东海，长命百岁", "心想事成，越活越年轻"],
            [66, 88, 99, 188, 520], "给长辈讲究 66/88/99 的彩头。"),
    "满月": (["长命百岁，健康平安", "聪明伶俐，茁壮成长"],
            [100, 200, 888, 1000], "给小宝宝的，图个吉利就好。"),
    "乔迁": (["乔迁之喜，越住越旺", "安居乐业，吉星高照"],
            [666, 888, 1666], "贺新居，双数吉利。"),
    "升学": (["金榜题名，前程似锦", "学业有成，鹏程万里"],
            [666, 888, 999], "贺金榜，666 一路顺。"),
    "开业": (["开业大吉，财源广进", "生意兴隆，日进斗金"],
            [666, 888, 1888, 6666], "贺开张，888 发发发。"),
}

_ALIAS = {
    "压岁钱": "压岁钱", "压岁": "压岁钱", "过年红包": "压岁钱", "给小孩红包": "压岁钱",
    "拜年": "拜年", "新年红包": "拜年", "春节红包": "拜年",
    "婚礼": "婚礼", "结婚": "婚礼", "随礼": "婚礼", "份子钱": "婚礼", "随份子": "婚礼",
    "生日": "生日", "寿": "生日", "祝寿": "生日",
    "满月": "满月", "百日": "满月", "弥月": "满月",
    "乔迁": "乔迁", "搬家": "乔迁", "新居": "乔迁", "新房": "乔迁",
    "升学": "升学", "金榜": "升学", "考上": "升学", "高考": "升学",
    "开业": "开业", "开张": "开业", "开店": "开业",
}


def occasions(config=None) -> list:
    return list(_merge(config).keys())


def _merge(config=None) -> dict:
    d = {k: (list(v[0]), list(v[1]), v[2]) for k, v in _OCCASIONS.items()}
    cfg = (config or {}).get("red_packet") if isinstance(config, dict) else None
    extra = (cfg or {}).get("occasions") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for occ, v in extra.items():
            if isinstance(v, dict):
                d[str(occ)] = (list(v.get("words") or []), list(v.get("amounts") or []), str(v.get("note", "")))
    return d


def find_occasion(utterance, config=None):
    """听出是什么场合的红包。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            cand = _ALIAS[word]
            if cand in _merge(config):
                return cand
    for occ in _merge(config):
        if occ in u:
            return occ
    return None


def lucky_meaning(amount) -> str:
    """某个数字的吉利寓意。查不到返回空。"""
    try:
        a = float(amount)
    except (TypeError, ValueError):
        return ""
    for amt, mean in _LUCKY:
        if abs(amt - a) < 1e-9:
            return mean
    return ""


def words_for(occasion, seed="", config=None) -> str:
    """某场合的一句红包祝词。"""
    occ = _ALIAS.get(str(occasion or ""), str(occasion or ""))
    d = _merge(config).get(occ)
    if not d or not d[0]:
        return ""
    return d[0][len(str(seed)) % len(d[0])]


def lucky_amounts(occasion, config=None) -> list:
    """某场合更搭的吉利数（带寓意）[(数, 寓意)]。"""
    occ = _ALIAS.get(str(occasion or ""), str(occasion or ""))
    d = _merge(config).get(occ)
    if not d:
        return []
    out = []
    for amt in d[1]:
        out.append((amt, lucky_meaning(amt) or "讨个吉利"))
    return out


def advise(occasion, seed="", config=None) -> str:
    """给红包参考：祝词 + 吉利数 + 忌讳，一段话。"""
    occ = _ALIAS.get(str(occasion or ""), str(occasion or ""))
    d = _merge(config).get(occ)
    if not d:
        return ""
    word = words_for(occ, seed, config)
    nums = "、".join(f"{_fmt_amt(a)}（{m}）" for a, m in lucky_amounts(occ, config))
    note = d[2]
    return (f"{occ}的红包，封面上可以写：「{word}」。"
            f"讨口彩的数字：{nums}。{note}（具体多少量力而行，心意最重要。）")


def _fmt_amt(a) -> str:
    return str(int(a)) if abs(a - int(a)) < 1e-9 else ("%.2f" % a)


def count(config=None) -> int:
    return len(_merge(config))


def is_red_packet_query(utterance, config=None) -> bool:
    """是不是在问红包（写啥/包多少/吉利数字）。"""
    u = str(utterance or "")
    has_rp = any(k in u for k in ("红包", "压岁钱", "份子钱", "随礼", "随份子"))
    if not has_rp:
        return False
    return any(k in u for k in ("写啥", "写什么", "祝词", "祝福", "包多少", "多少钱", "多少合适",
                                "吉利", "数字", "怎么写", "封面", "发多少", "给多少"))

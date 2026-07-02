"""单位换算：老人常问"一斤多少克""一亩多大""华氏多少度"——这一块真算给你。
重量、长度、面积、容量按市制/公制/英制互换，温度摄氏华氏单独算。
纯逻辑、可单测：parse_query 解析"几个什么换成什么"，convert 真换算，answer 给一句话。
"""

from __future__ import annotations

import re

# 各维度：单位别名 -> 折算到该维度"基准单位"的倍数
_DIMS = {
    "重量": ("克", {
        "克": 1.0, "g": 1.0, "千克": 1000.0, "公斤": 1000.0, "kg": 1000.0,
        "斤": 500.0, "市斤": 500.0, "两": 50.0, "钱": 5.0,
        "毫克": 0.001, "吨": 1_000_000.0, "磅": 453.592, "盎司": 28.3495,
    }),
    "长度": ("米", {
        "米": 1.0, "m": 1.0, "厘米": 0.01, "cm": 0.01, "毫米": 0.001, "mm": 0.001,
        "分米": 0.1, "千米": 1000.0, "公里": 1000.0, "km": 1000.0,
        "里": 500.0, "市里": 500.0, "市尺": 1 / 3, "尺": 1 / 3, "寸": 1 / 30,
        "英寸": 0.0254, "英尺": 0.3048, "英里": 1609.344, "海里": 1852.0,
    }),
    "面积": ("平方米", {
        "平方米": 1.0, "平米": 1.0, "平方厘米": 0.0001, "平方分米": 0.01,
        "平方千米": 1_000_000.0, "平方公里": 1_000_000.0, "公顷": 10000.0,
        "亩": 666.6667, "市亩": 666.6667, "公亩": 100.0,
    }),
    "容量": ("毫升", {
        "毫升": 1.0, "ml": 1.0, "升": 1000.0, "l": 1000.0, "立方米": 1_000_000.0,
        "立方厘米": 1.0, "加仑": 3785.41,
    }),
}

# 温度单独处理（不是简单倍数）
_TEMP = {"摄氏": "C", "摄氏度": "C", "℃": "C", "华氏": "F", "华氏度": "F", "℉": "F"}

_CN_DIGIT = {"零": 0, "一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5,
             "六": 6, "七": 7, "八": 8, "九": 9}


def _cn_num(s: str):
    """把简单中文数字转成数（支持 一~九十九、半、整数）。转不了返回 None。"""
    s = s.strip()
    if not s:
        return None
    if s == "半":
        return 0.5
    if "十" in s:
        a, _, b = s.partition("十")
        tens = _CN_DIGIT.get(a, 1 if a == "" else None)
        ones = _CN_DIGIT.get(b, 0 if b == "" else None)
        if tens is None or ones is None:
            return None
        return tens * 10 + ones
    if all(c in _CN_DIGIT for c in s):
        if len(s) == 1:
            return _CN_DIGIT[s]
    return _CN_DIGIT.get(s)


def _find_number(u: str):
    """抓第一个数，返回 (值, (起,止) 或 None)。抓不到默认 1（"一斤多少克"省了"一"）。"""
    m = re.search(r"\d+\.?\d*", u)
    if m:
        return float(m.group()), m.span()
    m2 = re.search(r"[零一两二三四五六七八九十]+|半", u)
    if m2:
        n = _cn_num(m2.group())
        if n is not None:
            return float(n), m2.span()
    return 1.0, None


def _unit_lexicon():
    """所有单位词 -> (维度, 规范名/温度标记)，按长度排序备用。"""
    lex = {}
    for dim, (_base, table) in _DIMS.items():
        for name in table:
            lex[name] = (dim, name)
    for name in _TEMP:
        lex[name] = ("温度", name)        # 规范名就用单位词本身（C/F 由 _TEMP 另查）
    return lex


def _scan_units(u: str, exclude=None):
    """扫出话里的单位，按位置排序，返回 [(pos, 维度, 规范名)]（同位置取最长）。
    exclude=(起,止) 命中数字的那段不当单位（如"两公斤"里的"两"是数字 2，不是单位两）。"""
    lex = _unit_lexicon()
    ex0, ex1 = exclude if exclude else (-1, -1)
    hits = []
    for name in sorted(lex, key=len, reverse=True):
        start = 0
        while True:
            i = u.find(name, start)
            if i < 0:
                break
            covered = any(p <= i < p + len(n2) for p, _d, n2 in hits)
            in_number = ex0 <= i < ex1            # 落在数字串里 → 不是单位
            if not covered and not in_number:
                hits.append((i, lex[name][0], lex[name][1]))
            start = i + len(name)
    hits.sort(key=lambda t: t[0])
    return hits


def convert(value, from_unit, to_unit):
    """同一维度内换算；温度走专门公式。单位不认/跨维度抛 ValueError。"""
    lex = _unit_lexicon()
    f = lex.get(from_unit)
    t = lex.get(to_unit)
    if not f or not t:
        raise ValueError("不认识的单位")
    if f[0] == "温度" or t[0] == "温度":
        if f[0] != "温度" or t[0] != "温度":
            raise ValueError("温度只能和温度互换")
        c = value if _TEMP[from_unit] == "C" else (value - 32) * 5 / 9
        return c if _TEMP[to_unit] == "C" else c * 9 / 5 + 32
    if f[0] != t[0]:
        raise ValueError("不是同一类单位，没法换")
    table = _DIMS[f[0]][1]
    return value * table[from_unit] / table[to_unit]


def _fmt_num(x: float) -> str:
    r = round(x, 4)
    if abs(r - round(r)) < 1e-9:
        return str(int(round(r)))
    return ("%.4f" % r).rstrip("0").rstrip(".")


def parse_query(utterance):
    """解析"几个A是多少B"，返回 (value, from_unit, to_unit)；解析不出返回 None。"""
    u = str(utterance or "")
    value, span = _find_number(u)
    units = _scan_units(u, exclude=span)
    if len(units) < 2:
        return None
    from_u = units[0][2]
    to_u = units[-1][2]
    if from_u == to_u:
        diff = [x for x in units if x[2] != from_u]
        if not diff:
            return None
        to_u = diff[-1][2]
    return (value, from_u, to_u)


def answer(utterance, config=None) -> str:
    """一句话回答换算。解析/换算不了返回空。"""
    pq = parse_query(utterance)
    if not pq:
        return ""
    value, from_u, to_u = pq
    try:
        out = convert(value, from_u, to_u)
    except ValueError as e:
        return f"这个换不了：{e}。"
    # 温度补「度」，但别给已带"度"的（如"华氏度"）再加一个
    suffix_from = "度" if (from_u in _TEMP and not from_u.endswith("度")) else ""
    suffix_to = "度" if (to_u in _TEMP and not to_u.endswith("度")) else ""
    return f"{_fmt_num(value)}{from_u}{suffix_from} ≈ {_fmt_num(out)}{to_u}{suffix_to}。"


def is_convert_query(utterance, config=None) -> bool:
    """是不是在问单位换算（有两个单位 + 换算意图词）。"""
    u = str(utterance or "")
    if not any(k in u for k in ("多少", "等于", "换算", "合多少", "是多少", "几", "换成", "折合", "相当于")):
        return False
    return parse_query(u) is not None


def count() -> int:
    """支持的单位总数（含温度）。"""
    return sum(len(t) for _b, t in _DIMS.values()) + len(_TEMP)

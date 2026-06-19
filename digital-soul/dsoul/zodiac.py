"""生肖星座：算属相、说星座——"1948年属什么""三月八号是什么星座"。图个亲切。
纯逻辑、可单测。
"""

from __future__ import annotations

import re

_ANIMALS = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
_ANIMAL_TRAIT = {
    "鼠": "机灵、会过日子", "牛": "踏实、肯吃苦", "虎": "有胆识、有冲劲",
    "兔": "温和、心细", "龙": "有气势、有福气", "蛇": "聪明、有主见",
    "马": "热情、爱自由", "羊": "善良、顾家", "猴": "灵活、点子多",
    "鸡": "勤快、利落", "狗": "忠厚、讲义气", "猪": "厚道、有口福",
}

# (星座, 起始MM-DD)，跨年的摩羯放最后兜底
_CONST = [
    ("水瓶座", (1, 20)), ("双鱼座", (2, 19)), ("白羊座", (3, 21)), ("金牛座", (4, 20)),
    ("双子座", (5, 21)), ("巨蟹座", (6, 22)), ("狮子座", (7, 23)), ("处女座", (8, 23)),
    ("天秤座", (9, 23)), ("天蝎座", (10, 24)), ("射手座", (11, 23)), ("摩羯座", (12, 22)),
]


def animal_of(year) -> str:
    """某年属什么。"""
    try:
        y = int(year)
    except (TypeError, ValueError):
        return ""
    return _ANIMALS[(y - 4) % 12]


def constellation(month, day) -> str:
    """某月某日是什么星座。"""
    try:
        m, d = int(month), int(day)
    except (TypeError, ValueError):
        return ""
    pick = "摩羯座"
    for name, (sm, sd) in _CONST:
        if (m, d) >= (sm, sd):
            pick = name
    return pick


def is_zodiac_query(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("属什么", "属啥", "什么生肖", "啥生肖", "什么星座",
                                "啥星座", "是什么座", "什么属相"))


def _zh_year(text):
    from .everyday_qa import zh2num
    m = re.search(r"(19|20)\d{2}", text)
    if m:
        return int(m.group())
    m = re.search(r"([零〇一二两三四五六七八九]{4})\s*年", text)
    if m:
        digs = "".join(str(zh2num(c)) for c in m.group(1))
        return int(digs) if digs.isdigit() else None
    return None


def answer(utterance) -> str:
    """按问话给属相或星座。"""
    u = str(utterance or "")
    if any(k in u for k in ("属", "生肖", "属相")):
        y = _zh_year(u)
        if y:
            a = animal_of(y)
            return f"{y}年属{a}，{a}年生的人，多半{_ANIMAL_TRAIT.get(a, '有福气')}。"
    if any(k in u for k in ("星座", "什么座")):
        from .everyday_qa import zh2num
        m = re.search(r"([一二三四五六七八九十\d]+)\s*月\s*([一二三四五六七八九十\d]+)\s*[日号]?", u)
        if m:
            mo, da = zh2num(m.group(1)), zh2num(m.group(2))
            c = constellation(mo, da) if mo and da else ""
            return f"那是{c}。" if c else ""
    return ""

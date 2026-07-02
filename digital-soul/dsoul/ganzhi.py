"""天干地支：干支纪年——"2026 年是丙午年""今年干支是什么"。配上属相，老黄历的算法。
六十年一甲子，循环不息。纯逻辑、可单测（传 now/year 可复现）。
"""

from __future__ import annotations

from datetime import datetime

_GAN = "甲乙丙丁戊己庚辛壬癸"          # 十天干
_ZHI = "子丑寅卯辰巳午未申酉戌亥"      # 十二地支
_ANIMALS = "鼠牛虎兔龙蛇马羊猴鸡狗猪"  # 对应生肖


def ganzhi_of(year) -> str:
    """某年的干支，如 2026 → 丙午。"""
    y = int(year)
    return _GAN[(y - 4) % 10] + _ZHI[(y - 4) % 12]


def animal_of(year) -> str:
    return _ANIMALS[(int(year) - 4) % 12]


def describe(year) -> str:
    y = int(year)
    return f"{y}年是{ganzhi_of(y)}年，生肖属{animal_of(y)}。"


def sexagenary() -> list:
    """六十甲子的完整循环。"""
    return [_GAN[i % 10] + _ZHI[i % 12] for i in range(60)]


def _extract_year(utterance, now=None):
    import re
    u = str(utterance or "")
    m = re.search(r"((?:19|20)\d{2})\s*年?", u)
    if m:
        return int(m.group(1))
    now = now or datetime.now()
    if "明年" in u:
        return now.year + 1
    if "去年" in u:
        return now.year - 1
    if "后年" in u:
        return now.year + 2
    if any(k in u for k in ("今年", "现在", "今")):
        return now.year
    return None


def answer(utterance, now=None) -> str:
    """回答干支纪年问题。算不出返回空。"""
    y = _extract_year(utterance, now)
    if y is None:
        y = (now or datetime.now()).year
    return describe(y)


def is_ganzhi_query(utterance) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("天干地支", "干支", "六十甲子", "甲子年", "什么甲子")):
        return True
    # "2026年是什么年/今年是什么年" 带干支语境
    if ("干支" in u) or (("天干" in u or "地支" in u)):
        return True
    return False

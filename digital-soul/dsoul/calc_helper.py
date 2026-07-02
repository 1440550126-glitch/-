"""生活小计算：打几折是多少钱、BMI算算胖不胖——随口报数字，帮你算清楚。
（加减乘除那种归 everyday_qa，这儿管打折和 BMI 这两样常用的。）

纯逻辑、可单测。数字解析尽量稳，算不出就老实说算不出。
"""

from __future__ import annotations

import re


def discount(price, zhe) -> float:
    """原价 price 打 zhe 折后的价。打8折=×0.8，打8.5折=×0.85。"""
    return round(float(price) * float(zhe) / 10, 2)


def parse_discount(utterance):
    """从'100块打8折'里算出折后价。算不出返回空。"""
    u = str(utterance or "")
    mp = re.search(r"(\d+(?:\.\d+)?)\s*(?:块|元|钱)?", u)
    mz = re.search(r"打\s*(\d+(?:\.\d+)?)\s*折", u)
    if not (mp and mz):
        return ""
    price = float(mp.group(1))
    zhe = float(mz.group(1))
    if not (0 < zhe <= 10):
        return ""
    final = discount(price, zhe)
    saved = round(price - final, 2)
    return f"原价 {price:g} 元，打 {zhe:g} 折后是 {final:g} 元，省了 {saved:g} 元。"


_BMI_CAT = [
    (18.5, "偏瘦，适当多吃点、增点肌肉"),
    (24, "正常，挺好，保持住"),
    (28, "偏胖了，管住嘴、迈开腿"),
    (999, "肥胖，要上点心了，少油少糖、多动动，必要时看看医生"),
]


def bmi(height_cm, weight_kg):
    """BMI = 体重(kg) / 身高(m)的平方。返回 (值, 评价)。"""
    h = float(height_cm)
    if h > 3:                                       # 当成厘米
        h = h / 100.0
    if h <= 0:
        return None
    val = round(float(weight_kg) / (h * h), 1)
    cat = next(c for thr, c in _BMI_CAT if val < thr)
    return (val, cat)


def parse_bmi(utterance):
    """从'身高170体重65'算 BMI。算不出返回空。"""
    u = str(utterance or "")
    mh = re.search(r"身高\s*(\d+(?:\.\d+)?)\s*(?:厘米|cm|公分|米|m)?", u)
    mw = re.search(r"体重\s*(\d+(?:\.\d+)?)\s*(?:公斤|kg|斤)?", u)
    if not (mh and mw):
        return ""
    h = float(mh.group(1))
    w = float(mw.group(1))
    if "斤" in u and "公斤" not in u and "kg" not in u.lower():
        w = w / 2.0                                 # 市斤换公斤
    r = bmi(h, w)
    if not r:
        return ""
    val, cat = r
    return f"你的 BMI 大约是 {val}（{cat}）。"


def is_calc_query(utterance) -> bool:
    u = str(utterance or "")
    if re.search(r"打\s*\d+(?:\.\d+)?\s*折", u):
        return True
    if ("bmi" in u.lower()) or ("身高" in u and "体重" in u):
        return True
    return False


def answer(utterance) -> str:
    u = str(utterance or "")
    if re.search(r"打\s*\d", u):
        return parse_discount(u)
    return parse_bmi(u)

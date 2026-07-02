"""日常小问答：长辈随口问的小事——三斤是几公斤、今天星期几、二加七等于几。
不用大模型也能答上，省得他们去翻手机。纯逻辑、可单测。
"""

from __future__ import annotations

import re
from datetime import datetime

_ZH = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
       "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "百": 100}

# 单位 → 基准量（重量基准=克，长度基准=厘米）
_WEIGHT = {"克": 1, "千克": 1000, "公斤": 1000, "斤": 500, "两": 50, "吨": 1_000_000}
_LENGTH = {"毫米": 0.1, "厘米": 1, "分米": 10, "米": 100, "尺": 100 / 3, "寸": 10 / 3,
           "里": 50000, "公里": 100000, "千米": 100000}
_WEEK = ["一", "二", "三", "四", "五", "六", "日"]


def zh2num(s):
    """中文数字（含十几、二十几）转整数；本就是数字则直接返回。"""
    s = str(s).strip()
    if s.isdigit():
        return int(s)
    if s in _ZH:
        return _ZH[s]
    if "十" in s:
        a, b = s.split("十", 1)
        tens = _ZH.get(a, 1) if a else 1
        ones = _ZH.get(b, 0) if b else 0
        return tens * 10 + ones
    try:
        return float(s)
    except ValueError:
        return None


def _num_in(text):
    m = re.search(r"\d+(?:\.\d+)?", text)
    if m:
        return float(m.group())
    m = re.search(r"[零〇一二两三四五六七八九十百]+", text)
    return zh2num(m.group()) if m else None


def convert(utterance):
    """X斤是多少公斤 / X米等于几厘米 → 一句换算结果；不是换算就空。"""
    u = str(utterance or "")
    for table, _name in ((_WEIGHT, "重量"), (_LENGTH, "长度")):
        units = sorted(table, key=len, reverse=True)
        found = [un for un in units if un in u]
        if len(found) >= 2:
            val = _num_in(u)
            if val is None:
                continue
            frm, to = found[0], found[1]
            # 第一个出现的单位是源、第二个是目标
            if u.find(frm) > u.find(to):
                frm, to = to, frm
            res = val * table[frm] / table[to]
            res = int(res) if abs(res - round(res)) < 1e-9 else round(res, 2)
            return f"{('%g' % val)}{frm}是 {res}{to}。"
    return ""


def arithmetic(utterance):
    """二加七 / 十减四 / 六乘七 / 二十除以四 → 结果；不是算术就空。"""
    u = str(utterance or "")
    ops = [("加上", "+"), ("加", "+"), ("减去", "-"), ("减", "-"), ("乘以", "*"),
           ("乘", "*"), ("除以", "/"), ("除", "/")]
    for word, op in ops:
        if word in u:
            a, b = u.split(word, 1)
            x, y = _num_in(a), _num_in(b)
            if x is None or y is None:
                continue
            if op == "+":
                r = x + y
            elif op == "-":
                r = x - y
            elif op == "*":
                r = x * y
            else:
                if y == 0:
                    return "除数不能是零哦。"
                r = x / y
            r = int(r) if abs(r - round(r)) < 1e-9 else round(r, 2)
            return f"等于 {r}。"
    return ""


def date_query(utterance, now=None):
    """今天星期几 / 今天几号 / 现在几点。"""
    u = str(utterance or "")
    now = now or datetime.now()
    if "星期几" in u or "周几" in u or "礼拜几" in u:
        return f"今天星期{_WEEK[now.weekday()]}。"
    if "几号" in u or "几月几" in u or "今天日期" in u:
        return f"今天是 {now.month} 月 {now.day} 号。"
    if "几点" in u or "现在时间" in u:
        return f"现在 {now.hour} 点 {now.minute} 分。"
    return ""


def answer(utterance, now=None):
    """挑对的小助手来答；都不沾返回空。"""
    return convert(utterance) or arithmetic(utterance) or date_query(utterance, now)

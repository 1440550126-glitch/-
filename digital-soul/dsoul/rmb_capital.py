"""人民币金额大写：把"1250.5"念成"壹仟贰佰伍拾元伍角整"——写收据、打借条、填支票用。
老人手写金额怕写错、怕被改，大写规范又难记。这一块照财务规矩转，规规矩矩不出错。
纯逻辑、可单测：to_capital 转大写，answer 从一句话里抓数额回答。
"""

from __future__ import annotations

import re

_DIGITS = "零壹贰叁肆伍陆柒捌玖"
_SMALL = ["", "拾", "佰", "仟"]
_BIG = ["", "万", "亿", "兆"]


def _section(num: int) -> str:
    """0~9999 转大写（含内部零，不含节单位）。"""
    s = str(num)
    L = len(s)
    res = ""
    zero = False
    for i, ch in enumerate(s):
        d = int(ch)
        pos = L - 1 - i
        if d == 0:
            zero = True
        else:
            if zero and res:
                res += "零"
            zero = False
            res += _DIGITS[d] + _SMALL[pos]
    return res


def _int_to_cn(n: int) -> str:
    """非负整数转大写（万/亿分节、零的归并）。"""
    if n == 0:
        return "零"
    sections = []
    while n > 0:
        sections.append(n % 10000)
        n //= 10000
    parts = []
    for idx in range(len(sections) - 1, -1, -1):
        sec = sections[idx]
        if sec == 0:
            if parts and not parts[-1].endswith("零"):
                parts.append("零")
            continue
        sec_str = _section(sec)
        if idx < len(sections) - 1 and sec < 1000:   # 高节末尾接低节、低节高位为0 → 补零
            sec_str = "零" + sec_str
        parts.append(sec_str + _BIG[idx])
    res = "".join(parts).rstrip("零")
    while "零零" in res:
        res = res.replace("零零", "零")
    return res


def to_capital(amount) -> str:
    """金额转人民币大写。支持负数、四舍五入到分（用 Decimal，避免浮点误差）。"""
    from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
    try:
        val = Decimal(str(amount))
    except (TypeError, ValueError, InvalidOperation):
        return ""
    sign = "负" if val < 0 else ""
    total_fen = int((abs(val) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    yuan = total_fen // 100
    jiao = (total_fen % 100) // 10
    fen = total_fen % 10

    yuan_part = (_int_to_cn(yuan) + "元") if yuan > 0 else ""
    if jiao == 0 and fen == 0:
        return sign + (yuan_part or "零元") + "整"
    frac = ""
    if jiao > 0:
        frac += _DIGITS[jiao] + "角"
    if fen > 0:
        if jiao == 0 and yuan > 0:
            frac += "零" + _DIGITS[fen] + "分"
        else:
            frac += _DIGITS[fen] + "分"
    else:  # 有角无分 → 收尾加"整"
        frac += "整"
    return sign + yuan_part + frac


def find_amount(utterance):
    """从话里抓一个金额数字（带千分位/小数）。抓不到返回 None。"""
    u = str(utterance or "").replace(",", "").replace("，", "")
    m = re.search(r"\d+\.?\d*", u)
    return float(m.group()) if m else None


def is_capital_query(utterance) -> bool:
    """是不是在求金额大写。"""
    u = str(utterance or "")
    if "大写" not in u and "大寫" not in u:
        return False
    # 要有钱相关线索（金额/元/块/钱）或一个数字
    return ("元" in u or "块" in u or "钱" in u or "金额" in u or
            re.search(r"\d", u) is not None)


def answer(utterance) -> str:
    """从一句话里抓金额并给大写。抓不到返回空。"""
    amt = find_amount(utterance)
    if amt is None:
        return ""
    cap = to_capital(amt)
    # 还原一个干净的数字显示
    shown = ("%f" % amt).rstrip("0").rstrip(".") if "." in ("%f" % amt) else str(int(amt))
    return f"{shown} 元，大写：{cap}。"

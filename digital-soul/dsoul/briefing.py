"""晨间关怀简报：把"今天是什么日子 / 谁该吃药复查 / 今天打算做啥 / 一句暖场白"
揉成一段早上主动说给家人听的话。区别于 butler 的"态势简报"——这一版是有温度的关怀。

纯函数、零依赖、可单测；Agent.care_briefing() 负责取数后调用本模块拼装。
"""

from __future__ import annotations

from datetime import datetime


def time_greeting(now=None) -> str:
    """按当下时辰给一句问候。"""
    h = (now or datetime.now()).hour
    if 5 <= h < 9:
        return "早上好"
    if 9 <= h < 12:
        return "上午好"
    if 12 <= h < 14:
        return "中午好"
    if 14 <= h < 18:
        return "下午好"
    if 18 <= h < 23:
        return "晚上好"
    return "夜深了"


def _clip(items, n):
    items = [str(x).strip() for x in (items or []) if str(x).strip()]
    return items[:n]


def compose_briefing(name=None, occasions=None, care=None, agenda=None,
                     last_words=None, encouragement=None, now=None) -> str:
    """拼一段晨间关怀。各块都可缺省，缺了就跳过，绝不堆空话。"""
    L = []
    head = time_greeting(now)
    if name:
        head += f"，{name}"
    L.append(head + "。")

    occ = _clip(occasions, 3)
    if occ:
        L.append(f"今天是{'、'.join(occ)}。")
        lw = _clip(last_words, 1)
        if lw:
            L.append(f"我一直想对你说：「{lw[0]}」")

    care = _clip(care, 4)
    if care:
        L.append("有几件惦记的事：" + "；".join(care) + "。")

    agenda = _clip(agenda, 3)
    if agenda:
        L.append("今天打算：" + "、".join(agenda) + "。")

    enc = (encouragement or "").strip()
    L.append(enc if enc else "今天也要好好的。")
    return " ".join(L)

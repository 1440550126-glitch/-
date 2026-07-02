"""周年祭 / 纪念仪式：到了忌日、冥诞、结婚纪念这些日子，不只提一句"今天是…"，
而是带一家人走一个小小的仪式——静一静、说说回忆、读一句 TA 的话、点一支心烛。

判断今天/近期是哪个纪念日、第几个年头，并生成有温度的仪式步骤。纯逻辑、可单测。
Agent.anniversaries_today() / remembrance_ritual() 调用本模块。
"""

from __future__ import annotations

from datetime import date, datetime


def _parse_md(s):
    """'MM-DD' 或 'YYYY-MM-DD' → (month, day, year|None)，解析不了返回 None。"""
    parts = str(s).strip().split("-")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    if len(nums) == 2:
        return nums[0], nums[1], None
    if len(nums) == 3:
        return nums[1], nums[2], nums[0]
    return None


def anniversaries_today(dates, now=None) -> list:
    """今天是哪些纪念日，各第几个年头。

    dates: { '忌日': '2019-04-05', '冥诞': '1948-08-12', ... }
    返回 [(name, years|None), ...]
    """
    now = now or datetime.now()
    out = []
    for name, when in (dates or {}).items():
        md = _parse_md(when)
        if not md:
            continue
        month, day, year = md
        if (now.month, now.day) == (month, day):
            years = (now.year - year) if year else None
            out.append((str(name), years))
    return out


def days_until(dates, now=None, within=30) -> list:
    """近 within 天内将到的纪念日：[(name, days_left, years|None), ...]，按远近排序。"""
    now = now or datetime.now()
    today = now.date()
    out = []
    for name, when in (dates or {}).items():
        md = _parse_md(when)
        if not md:
            continue
        month, day, year = md
        try:
            nxt = date(today.year, month, day)
        except ValueError:
            continue
        if nxt < today:
            try:
                nxt = date(today.year + 1, month, day)
            except ValueError:
                continue
        left = (nxt - today).days
        if 0 < left <= within:
            years = (nxt.year - year) if year else None
            out.append((str(name), left, years))
    out.sort(key=lambda t: t[1])
    return out


# 标签里带"人"的纪念日类型（用于从"张爸的忌日"里抽出"张爸"）
_PERSON_OCCASIONS = ("周年祭", "忌日", "冥诞", "祭日", "诞辰")


def who_of(label) -> str:
    """从纪念日标签里抽出缅怀的人："张爸的忌日"→"张爸"；抽不出（如"结婚纪念日"）返回 ""。"""
    s = str(label or "").strip()
    for t in _PERSON_OCCASIONS:
        if s.endswith(t) and len(s) > len(t):
            return s[: -len(t)].rstrip("的").strip()
    return ""


def ritual_steps(occasion, who=None, last_words=None, memories=None, years=None) -> list:
    """生成一段纪念仪式的步骤话（一步一句，便于一句句念给家人）。

    occasion：纪念日名，可为完整标签（如"张爸的忌日"）；who：缅怀的人（可空）。
    """
    who = (who or "").strip()
    yr = f"，{years}周年了" if years else ""
    steps = [f"今天是{occasion}{yr}。我们一起静一静。"]
    mems = [str(m).strip() for m in (memories or []) if str(m).strip()]
    if mems:
        steps.append("还记得吗——" + "；".join(m.rstrip("。.") for m in mems[:2]) + "。")
    steps.append(f"谁来说一件关于{who}、最想再讲一遍的事？" if who
                 else "谁来说一件、最想再讲一遍的事？")
    if last_words:
        steps.append(f"{who or 'TA'}留过一句话给我们：「{str(last_words).strip()}」")
    steps.append(f"我替大家点一支心烛。{who or '你'}，我们都好好的，请放心。")
    return steps


def candle(who="TA") -> str:
    """一支心烛。"""
    return f"🕯 一支心烛，敬{(who or 'TA').strip() or 'TA'}。"

"""今天提要：把该知道的事汇成一段——天气穿衣、该吃的药、就医安排、谁过生日、什么节、
养生贴士、花草要不要浇、谁好久没联系。早上说一遍，心里有数。

把零散的主动提醒整合成一段连贯的话。纯逻辑、可单测：gather 收集、compose 成段。
"""

from __future__ import annotations

from datetime import datetime


def gather(agent, now=None) -> dict:
    """从各模块收集今天要点；每块各自降级为空。"""
    now = now or datetime.now()
    d: dict = {}

    def _try(fn, default=""):
        try:
            return fn()
        except Exception:
            return default

    d["weather"] = _try(lambda: agent.dressing_advice()
                        if (getattr(agent, "sensors", None) or {}).get("temperature") is not None
                        else "")
    d["festival"] = _try(lambda: agent.festival_today() or "")
    d["birthday"] = _try(lambda: agent.birthday_reminders(within=3, now=now) if getattr(agent, "family", None) else "")
    d["anniversary"] = _try(lambda: agent.spouse_anniversary() or agent.spouse_anniversary_countdown()
                            if getattr(agent, "spouse", None) else "")
    d["meds"] = _try(lambda: "；".join(agent.medications.reminders(now))
                     if getattr(agent, "medications", None) is not None else "")
    d["appts"] = _try(lambda: "；".join(agent.appointments.reminders(now, within=3))
                      if getattr(agent, "appointments", None) is not None else "")
    d["wellness"] = _try(lambda: agent.wellness_tip(now))
    d["plants"] = _try(lambda: agent.plants.reminders(now)
                       if getattr(agent, "plants", None) is not None else "")
    d["touch"] = _try(lambda: agent.touch.reminders(now)
                      if getattr(agent, "touch", None) is not None else "")
    d["habits"] = _try(lambda: ("今天的" + "、".join(agent.habits_book.pending(now)) + "还没打卡")
                       if getattr(agent, "habits_book", None) is not None
                       and agent.habits_book.pending(now) else "")
    d["chores"] = _try(lambda: agent.board.describe()
                       if getattr(agent, "board", None) is not None
                       and agent.board.pending() else "")
    return d


def compose(parts, greeting="") -> str:
    """把要点串成一段连贯的提要。"""
    order = ["festival", "weather", "birthday", "anniversary", "meds", "appts",
             "chores", "wellness", "plants", "touch", "habits"]
    body = [str(parts.get(k, "")).strip() for k in order]
    body = [b for b in body if b]
    if not body:
        return (greeting + " 今天没什么特别要紧的，安安稳稳过就好。").strip()
    head = greeting or "跟你说说今天："
    return f"{head} " + " ".join(b.rstrip("。") + "。" for b in body)


def morning_digest(agent, now=None, greeting="") -> str:
    return compose(gather(agent, now), greeting=greeting)

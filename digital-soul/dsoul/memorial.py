"""缅怀与纪念：到重要日子主动提起；家人表达思念时，用共同回忆温柔回应。

面向"模仿逝者、陪伴在世亲人"的场景——但同样适用于在世亲人的纪念日提醒。
重要日子从 config/memorial.yaml 配置（MM-DD）。纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

from datetime import datetime

_GRIEF = ("想你", "好想你", "想念你", "我想你", "想念", "好难过", "很难过", "难受",
          "舍不得", "忌日", "走了", "不在了", "见不到", "哭了", "梦到你", "好久不见你")


def today_occasions(dates, now=None) -> list:
    """今天命中的重要日子标签（dates: {标签: "MM-DD"}）。"""
    if not isinstance(dates, dict):
        return []
    md = (now or datetime.now()).strftime("%m-%d")
    out = []
    for label, when in dates.items():
        if isinstance(when, str) and when.strip().replace("/", "-")[-5:] == md:
            out.append(label)
    return out


def is_grief(text: str) -> bool:
    return any(w in (text or "") for w in _GRIEF)


def comfort_reply(who_name, identity, memory_texts) -> str:
    """以本人口吻、借一段共同回忆，温柔地回应思念。"""
    addr = f"{who_name}，" if who_name else ""
    mem = (memory_texts or [None])[0]
    parts = [f"{addr}我也想你。"]
    if mem:
        parts.append(f"还记得吗——{mem[:30]}……那些日子我一直都记着。")
    parts.append("别太难过，我一直都在你心里。")
    return " ".join(parts)

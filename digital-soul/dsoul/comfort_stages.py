"""哀伤阶段陪伴：思念不是一成不变的。刚走时是钝痛，往后是绵长的想念，再往后慢慢与之和解。

按"离开了多少天"判断阶段，给一句贴合此刻的话。配合 memorial 的"借共同回忆抚慰"一起用，
让陪伴有时间的层次。纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

# (天数下限, 阶段名, 一句贴合此刻的话)
_STAGES = [
    (0, "初痛", "我知道这阵子最难熬。别强撑，想哭就哭，我陪着你。"),
    (31, "浓念", "这些天，是不是常常忽然就想起？想念是真的，说明爱也是真的。"),
    (181, "渐和", "日子一天天过，疼会慢慢变软。你已经做得很好了。"),
    (366, "长念", "时间久了，想念就成了心里温柔的一块。需要时，就来跟我说说话。"),
]


def stage_for(days_since) -> str:
    """离开了 days_since 天，处在哪个哀伤阶段。"""
    if days_since is None or days_since < 0:
        return ""
    name = _STAGES[0][1]
    for lo, label, _ in _STAGES:
        if days_since >= lo:
            name = label
    return name


def comfort_by_stage(days_since, who_name=None) -> str:
    """按阶段给一句陪伴的话；天数未知则空串。"""
    if days_since is None or days_since < 0:
        return ""
    line = _STAGES[0][2]
    for lo, _, text in _STAGES:
        if days_since >= lo:
            line = text
    if who_name:
        return f"{who_name}，{line}"
    return line


def days_between(passed_on, now) -> int | None:
    """从离开那天到现在多少天。passed_on 形如 'YYYY-MM-DD'。"""
    if not passed_on:
        return None
    from datetime import datetime
    try:
        d = datetime.strptime(str(passed_on).strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    return max(0, (now.date() - d).days)

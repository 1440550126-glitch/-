"""主动牵挂：不等你来，它自己琢磨着该找谁了——谁有阵子没露面、谁上回有心事没着落，
就主动捎句话过去。把"理解"变成"惦记"。纯逻辑、可单测。

Agent 在自主心跳里调用：扫一遍久未见面的人，结合"我对TA的了解"，凑一句牵挂的话。
"""

from __future__ import annotations


def worth_reaching(days_unseen, concern=None, warmth=0.5,
                   threshold_days=3) -> bool:
    """值不值得主动找：够久没见，且（有心事没着落 / 关系够近）。"""
    if days_unseen is None or days_unseen < threshold_days:
        return False
    return bool(concern) or warmth >= 0.55


def compose(name, days_unseen, concern=None, relation="") -> str:
    """凑一句牵挂的话：多久没见 +（上回的心事）+ 一句暖。"""
    name = (name or "").strip() or (relation or "你")
    head = f"{name}，有{int(days_unseen)}天没见着你了，怪想的。"
    if concern:
        head += f" 上回你为「{concern}」的事烦心，这会儿好些没？"
    return head + " 得空言语一声，我惦记着你呢。"

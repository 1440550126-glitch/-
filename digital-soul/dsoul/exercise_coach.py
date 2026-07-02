"""动一动 / 养生操：陪老人和久坐的人活动活动筋骨——散步、护颈、拉伸、八段锦。
一步一步带着做，慢就好、舒服就好。present-tense、可单测。
"""

from __future__ import annotations

_ROUTINES = {
    "散步": ["饭后慢走二十分钟", "抬头挺胸，步子放稳", "注意脚下，别赶、别逞强"],
    "护颈": ["缓缓低头、抬头，各十次", "左右转头，各十次", "耸耸肩、转转肩，放松"],
    "拉伸": ["伸个大懒腰，深呼吸三次", "踮脚尖十次", "转转脚踝和手腕"],
    "八段锦": ["两手托天理三焦", "左右开弓似射雕", "调理脾胃须单举", "五劳七伤往后瞧"],
    "护腰": ["双手叉腰，缓缓转腰", "弯腰够脚尖，别太勉强", "靠墙站直三分钟"],
}

# 触发词 → 套路名
_NAMES = {
    "散步": ("散步", "走路", "遛弯"),
    "护颈": ("脖子", "颈椎", "护颈", "肩颈"),
    "拉伸": ("拉伸", "伸展", "舒展"),
    "八段锦": ("八段锦", "养生操", "气功"),
    "护腰": ("腰", "护腰"),
}


def routines() -> list:
    return list(_ROUTINES.keys())


def find_routine(utterance):
    u = utterance or ""
    for name, kws in _NAMES.items():
        if any(k in u for k in kws):
            return name
    return None


def guide(name) -> str:
    """带着做一套：一步一句。"""
    steps = _ROUTINES.get(name)
    if not steps:
        return ""
    body = "；".join(f"{i + 1}）{s}" for i, s in enumerate(steps))
    return f"来，跟我做{name}：{body}。慢慢来，舒服就好。"


def suggest(now=None) -> str:
    """按时候挑个合适的：饭后散步、久坐护颈。"""
    from datetime import datetime
    h = (now or datetime.now()).hour
    if h in (8, 13, 19):
        return guide("散步")
    if 9 <= h <= 17:
        return guide("护颈")
    return guide("拉伸")


def is_exercise_query(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("动一动", "活动活动", "做个操", "锻炼一下", "带我做",
                                "养生操", "活动筋骨", "教我锻炼"))

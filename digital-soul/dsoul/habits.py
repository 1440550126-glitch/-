"""行为习惯：让分身知道「这个点 TA 一般在做什么」，举手投足像 TA。

从 identity.daily_life（生前的日常）按时段归类，给定当下时间就说出 TA 此刻惯常的活动——
模仿的不只是话，还有作息与举止。纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

from datetime import datetime

_BUCKET_KW = {
    "早上": ("早上", "早晨", "清晨", "起床", "早饭", "早餐", "咖啡"),
    "中午": ("中午", "午饭", "午休", "午餐"),
    "下午": ("下午", "茶歇", "上班", "工作", "开会", "写代码", "带团队"),
    "晚上": ("晚上", "晚饭", "晚餐", "夜里", "睡前", "遛狗", "散步", "陪家人", "陪"),
    "周末": ("周末", "休息日", "篮球", "捣鼓"),
}


def _bucket(hour: int, weekend: bool) -> str:
    if weekend:
        return "周末"
    if hour < 11:
        return "早上"
    if hour < 14:
        return "中午"
    if hour < 18:
        return "下午"
    return "晚上"


def current_activity(daily_life, now=None) -> str:
    """此刻 TA 惯常在做的一件事（取自 daily_life）。匹配不到返回空串。"""
    if not daily_life:
        return ""
    now = now or datetime.now()
    weekend = now.weekday() >= 5
    b = _bucket(now.hour, weekend)
    for entry in daily_life:
        if any(k in entry for k in _BUCKET_KW.get(b, ())):
            return entry
    if weekend:                                  # 周末没匹配到就退回任意周末项
        for entry in daily_life:
            if any(k in entry for k in _BUCKET_KW["周末"]):
                return entry
    return ""

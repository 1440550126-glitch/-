"""情景预测：从过往规律里预感主人接下来可能想做 / 需要什么，提前一步。

借鉴"预期型 / 前摄智能体"：把对话日记按时段聚合，学出"这个点你常聊 / 常做什么"，
给定当下时间就预感一句、主动提出。纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from .curiosity import _COMMON
from .reflect import _bigrams

# 时段 / 时间词本身不是"活动"，不拿来预测
_SKIP = _COMMON | {"早上", "中午", "下午", "晚上", "深夜", "昨天", "今天", "明天", "周末", "傍晚", "凌晨"}


def _bucket(hour: int) -> str:
    if hour < 6:
        return "深夜"
    if hour < 11:
        return "早上"
    if hour < 14:
        return "中午"
    if hour < 18:
        return "下午"
    return "晚上"


def learn(entries):
    """对话日记 → {时段: Counter(高频主题)}。"""
    by_bucket: dict = {}
    for e in entries:
        ts, u = e.get("ts"), e.get("utterance", "")
        if not ts or not u:
            continue
        try:
            b = _bucket(datetime.fromtimestamp(ts).hour)
        except Exception:
            continue
        by_bucket.setdefault(b, Counter()).update(set(_bigrams(u)) - _SKIP)
    return by_bucket


def predict(entries, now=None, min_count: int = 2) -> str:
    """给定当下时间，预感一句这个点常出现的事。规律不足则返回空。"""
    now = now or datetime.now()
    c = learn(entries).get(_bucket(now.hour))
    if not c:
        return ""
    for word, n in c.most_common():
        if n >= min_count:
            return f"这个点（{_bucket(now.hour)}）你常念叨「{word}」，要我搭把手吗？"
    return ""

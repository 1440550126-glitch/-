"""记忆遗忘曲线（Ebbinghaus）：让记忆像人一样有强弱、会淡忘、可被唤醒。

每条记忆有一个随时间衰减的"强度"：retention = exp(-Δt / stability)。
- stability（稳定度）越高衰减越慢，由"重要性 + 被回忆次数"决定；
- 重要性来自情感（深情/悲伤…比平静更难忘）、标签（领悟/办成的事）、是否里程碑（带年份）；
- 每次被回忆都会刷新计时并提升稳定度（间隔重复）。

纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

import math
import time

_EMO_IMPORTANCE = {
    "深情": 0.9, "悲伤": 0.8, "怀念": 0.8, "恐惧": 0.8,
    "喜悦": 0.7, "愤怒": 0.7, "平静": 0.3,
}


def importance(item: dict) -> float:
    """0~1 的重要性：情感越浓、越是里程碑/领悟，越重要。"""
    base = _EMO_IMPORTANCE.get(item.get("emotion"), 0.4)
    tags = item.get("tags") or []
    if any(t in tags for t in ("deed", "reflection", "领悟", "派活")):
        base = max(base, 0.7)
    if item.get("when"):                       # 带年份 = 里程碑
        base = min(1.0, base + 0.1)
    return max(0.0, min(1.0, base))


def stability(item: dict) -> float:
    """以"天"为尺度的稳定度：越重要、被回忆越多，衰减越慢。"""
    recalls = item.get("recalls", 0)
    return 7.0 + importance(item) * 60.0 + recalls * 30.0


def strength(item: dict, now: float | None = None) -> float:
    """当前记忆强度（0~1）。距离上次回忆/写入越久越弱。"""
    now = time.time() if now is None else now
    ref = item.get("last_recall") or item.get("created") or now
    age_days = max(0.0, (now - ref) / 86400.0)
    return math.exp(-age_days / stability(item))


def classify(s: float) -> str:
    return "清晰" if s >= 0.66 else ("模糊" if s >= 0.33 else "淡忘")

"""Predict Anything（简版）：多信号汇成"接下来可能…"的预测，带置信度，并从反馈中自我校准。

每个信号是一个轻量"预测器"（时段习惯 / 近期热点…），各给 (标签, 原始置信, 来源)。
聚合后用从反馈学到的校准（各来源命中率）调整置信度——你说"猜对 / 没猜对"，它越来越准。
（思路参考开源项目 MiroFish "Predict Anything" 的可校准预测理念。）纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from .anticipate import _SKIP, _bucket, learn
from .reflect import _bigrams


def _time_signal(entries, now):
    c = learn(entries).get(_bucket(now.hour))
    if not c:
        return None
    for w, n in c.most_common():
        if n >= 2:
            return (f"这个点（{_bucket(now.hour)}）你常念叨「{w}」，要我搭把手吗？",
                    min(0.9, 0.4 + 0.12 * n), "时段习惯")
    return None


def _recent_signal(entries, now=None):
    c: Counter = Counter()
    for e in entries[-30:]:
        c.update(set(_bigrams(e.get("utterance", ""))) - _SKIP)
    if not c:
        return None
    w, n = c.most_common(1)[0]
    if n < 3:
        return None
    return (f"你最近老把「{w}」挂嘴边，接下来八成还会提到。", min(0.85, 0.3 + 0.1 * n), "近期热点")


def predict(entries, now=None, calib=None):
    """聚合信号 → 置信度最高的一条预测（dict）。规律不足返回 None。"""
    now = now or datetime.now()
    sigs = [s for s in (_time_signal(entries, now), _recent_signal(entries, now)) if s]
    if not sigs:
        return None
    out = []
    for label, raw, src in sigs:
        f = calib.factor(src) if calib is not None else 1.0
        out.append({"label": label, "confidence": round(min(0.97, raw * f), 2), "source": src})
    out.sort(key=lambda x: -x["confidence"])
    return out[0]


class Calibration:
    """从"猜对 / 没猜对"的反馈里，学每个信号来源的可信度系数。"""

    def __init__(self, path) -> None:
        self.path = Path(path)
        self.stats: dict = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self.stats = json.loads(self.path.read_text(encoding="utf-8")).get("stats", {})
            except Exception:
                self.stats = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"stats": self.stats}, ensure_ascii=False, indent=2), encoding="utf-8")

    def factor(self, src: str) -> float:
        s = self.stats.get(src, {"hit": 0, "miss": 0})
        return max(0.4, min(1.3, 2 * (s["hit"] + 1) / (s["hit"] + s["miss"] + 2)))  # 起步 1.0

    def feedback(self, src: str, correct: bool) -> None:
        s = self.stats.setdefault(src, {"hit": 0, "miss": 0})
        s["hit" if correct else "miss"] += 1
        self._save()

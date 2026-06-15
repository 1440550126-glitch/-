"""七情（喜·怒·哀·惧·爱·恶·欲）情绪状态。

随互动起伏、随时间回落，并把当前主导情绪注入提示词，让回应带上"人味"。
纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

import time

from .annotate import classify_emotion

SEVEN = ["喜", "怒", "哀", "惧", "爱", "恶", "欲"]

# annotate 的情感标签 -> 七情增量
_MAP = {
    "喜悦": {"喜": 0.40},
    "悲伤": {"哀": 0.40},
    "愤怒": {"怒": 0.40},
    "恐惧": {"惧": 0.40},
    "深情": {"爱": 0.40, "欲": 0.10},
    "怀念": {"哀": 0.20, "爱": 0.20},
    "平静": {},
}

_DESC = {
    "喜": "心情愉悦",
    "怒": "有点生气",
    "哀": "有些低落",
    "惧": "有点不安",
    "爱": "满心爱意",
    "恶": "有点反感",
    "欲": "渴望陪伴、有点小情绪",
}


class EmotionState:
    def __init__(self, baseline: float = 0.1, decay_per_min: float = 0.15) -> None:
        self.baseline = baseline
        self.decay = decay_per_min
        self.levels = {e: baseline for e in SEVEN}
        self._last = time.time()

    def _tick(self, now: float | None = None) -> None:
        now = time.time() if now is None else now
        step = self.decay * max(0.0, (now - self._last) / 60.0)
        for e, v in self.levels.items():  # 向基线回落
            if v > self.baseline:
                self.levels[e] = max(self.baseline, v - step)
            else:
                self.levels[e] = min(self.baseline, v + step)
        self._last = now

    def feel(self, deltas: dict, now: float | None = None) -> None:
        self._tick(now)
        for e, d in deltas.items():
            if e in self.levels:
                self.levels[e] = max(0.0, min(1.0, self.levels[e] + d))

    def observe(self, text: str, speaker: dict | None = None, now: float | None = None) -> None:
        """根据一句话 + 说话人关系，更新情绪。"""
        deltas = dict(_MAP.get(classify_emotion(text)["label"], {}))
        if speaker:
            if speaker.get("guard"):
                deltas["爱"] = deltas.get("爱", 0) + 0.20
                deltas["欲"] = deltas.get("欲", 0) + 0.10
            if not speaker.get("obey", True):
                deltas["恶"] = deltas.get("恶", 0) + 0.30
        self.feel(deltas, now)

    def mood(self, now: float | None = None) -> tuple[str, float]:
        self._tick(now)
        top = max(self.levels, key=lambda k: self.levels[k])
        return top, self.levels[top]

    def prompt_hint(self, now: float | None = None) -> str:
        top, val = self.mood(now)
        if val < self.baseline + 0.08:
            return ""  # 情绪平淡就不强加
        return f"你此刻的情绪：{_DESC[top]}（{top}）。让语气自然地流露这种情绪，别刻意。"

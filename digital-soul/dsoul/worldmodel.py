"""世界模型：分身对世界 / 主人的"信念"，带置信度，会随证据增减、并自我修正。

每条信念由支持 / 反对的证据数决定置信度：confidence = support /(support + contradict)。
反复印证则越笃定（support 有上限，避免一句话推不动）；遇到相反信号则动摇、
甚至翻转——像人一样会改主意。纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

import json
from pathlib import Path

_CEILING = 6   # support 上限：让"自我修正"始终推得动


class WorldModel:
    def __init__(self, path) -> None:
        self.path = Path(path)
        self.beliefs: dict = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self.beliefs = json.loads(self.path.read_text(encoding="utf-8")).get("beliefs", {})
            except Exception:
                self.beliefs = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"beliefs": self.beliefs}, ensure_ascii=False, indent=2), encoding="utf-8")

    def reinforce(self, key: str, statement: str, n: int = 1) -> None:
        b = self.beliefs.setdefault(key, {"statement": statement, "support": 0, "contradict": 0})
        b["statement"] = statement
        b["support"] = min(_CEILING, b["support"] + n)
        self._save()

    def weaken(self, key: str, n: int = 1) -> None:
        if key in self.beliefs:
            self.beliefs[key]["contradict"] += n
            self._save()

    def confidence(self, key: str) -> float:
        b = self.beliefs.get(key)
        if not b:
            return 0.0
        s, c = b["support"], b["contradict"]
        return s / (s + c) if (s + c) else 0.0

    def top(self, k: int = 6, min_conf: float = 0.6):
        scored = [(self.confidence(key), b["statement"]) for key, b in self.beliefs.items()]
        return [(round(c, 2), s) for c, s in sorted(scored, key=lambda x: -x[0]) if c >= min_conf][:k]

    def shaky(self, k: int = 4):
        scored = [(self.confidence(key), b["statement"]) for key, b in self.beliefs.items()
                  if (b["support"] + b["contradict"]) > 0]
        return [(round(c, 2), s) for c, s in sorted(scored, key=lambda x: x[0]) if c < 0.6][:k]

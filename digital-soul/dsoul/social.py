"""社交记忆：分身对每个人记着一份"亲疏冷暖"——上次见是什么时候、聊过什么、
这段关系是热是淡。每次互动按情绪微调，于是它会"好久没见你了""上回你提的事"。

本地持久化为干净 JSON。纯逻辑、可单测。属于 Generative Agents 的社会记忆那一块。
"""

from __future__ import annotations

import json
import time
from pathlib import Path

# 七情 → 这次互动让关系变暖/变凉多少
_WARMTH = {"喜": 0.08, "乐": 0.08, "爱": 0.12, "欲": 0.03,
           "哀": -0.03, "惧": -0.04, "怒": -0.10, "恶": -0.12}


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


class SocialLog:
    def __init__(self, path) -> None:
        self.path = Path(path)
        self.people: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self.people = json.loads(self.path.read_text(encoding="utf-8")).get("people", {})
            except Exception:
                self.people = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"people": self.people}, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    def record(self, name) -> dict:
        return self.people.get(name, {"warmth": 0.5, "count": 0, "last_seen": None, "topics": []})

    def note(self, name, emotion=None, topic=None, now=None) -> dict:
        """记一次互动：按情绪调亲疏、更新上次见面与近期话题。"""
        name = (name or "").strip()
        if not name:
            return {}
        now = time.time() if now is None else now
        r = dict(self.record(name))
        r["warmth"] = round(_clamp(r["warmth"] + _WARMTH.get(emotion, 0.01)), 3)
        r["count"] = r.get("count", 0) + 1
        r["last_seen"] = now
        if topic:
            topics = [t for t in r.get("topics", []) if t != topic]
            topics.append(str(topic))
            r["topics"] = topics[-5:]
        self.people[name] = r
        self._save()
        return r

    def warmest(self, k=3) -> list:
        items = sorted(self.people.items(), key=lambda kv: -kv[1].get("warmth", 0))
        return [(n, d["warmth"]) for n, d in items[:k]]

    def cooled(self, days=14, now=None) -> list:
        """太久没见的人（按上次见面）。"""
        now = time.time() if now is None else now
        out = []
        for n, d in self.people.items():
            ls = d.get("last_seen")
            if ls is not None and (now - ls) >= days * 86400:
                out.append((n, int((now - ls) / 86400)))
        return sorted(out, key=lambda x: -x[1])

    def describe(self, name) -> str:
        r = self.record(name)
        if not r.get("count"):
            return f"我跟{name}还没怎么打过交道呢。"
        warm = r["warmth"]
        tone = "很亲" if warm >= 0.7 else ("不远不近" if warm >= 0.4 else "有点生分")
        topics = r.get("topics") or []
        tail = ("，上回还聊到" + "、".join(topics[-2:])) if topics else ""
        return f"我跟{name}的关系{tone}（见过 {r['count']} 回）{tail}。"

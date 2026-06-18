"""成长记录：替你记着孩子/孙辈的成长点滴——第一次叫爷爷、掉了第一颗牙、运动会得奖、
量了身高。攒成一条成长线，想起来能一桩桩讲给TA听。本地持久化，纯逻辑、可单测。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

# 成长里程碑的识别词
MARKS = ("会走路", "会说话", "会叫", "第一次", "掉牙", "掉了第一颗牙", "长高", "上学",
         "入学", "得奖", "拿了奖", "学会", "考了", "满月", "周岁", "百天", "会跑",
         "会自己", "毕业", "运动会", "第一名", "断奶", "会爬")


def detect_milestone(utterance) -> bool:
    u = utterance or ""
    return any(m in u for m in MARKS)


class GrowthLog:
    def __init__(self, path) -> None:
        self.path = Path(path)
        self.items: list[dict] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self.items = json.loads(self.path.read_text(encoding="utf-8")).get("items", [])
            except Exception:
                self.items = []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"items": self.items}, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    def record(self, child, milestone, when="", now=None) -> dict | None:
        child = (child or "").strip()
        milestone = (milestone or "").strip()
        if not child or not milestone:
            return None
        it = {"child": child, "milestone": milestone,
              "date": (when or (now or datetime.now()).strftime("%Y-%m-%d")).strip()}
        self.items.append(it)
        self._save()
        return it

    def for_child(self, name) -> list:
        n = (name or "").strip()
        return [it for it in self.items if n and (it["child"] in n or n in it["child"])]

    def timeline(self, name) -> list:
        return sorted(self.for_child(name), key=lambda it: it["date"])

    def latest(self, name, k=3) -> list:
        return self.timeline(name)[-k:][::-1]

    def describe(self, name) -> str:
        ms = self.timeline(name)
        if not ms:
            return f"还没记下{name}的成长点滴呢，有啥新鲜事跟我说。"
        return f"{name}这一路：" + "；".join(
            f"{it['date']} {it['milestone']}" for it in ms) + "。"

    def recall(self, name) -> str:
        """带着暖意把成长一桩桩讲出来。"""
        ms = self.timeline(name)
        if not ms:
            return ""
        bits = "；".join(it["milestone"] for it in ms[:5])
        return f"看着{name}一点点长大，桩桩我都记着——{bits}。日子过得真快啊。"

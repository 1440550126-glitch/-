"""待办清单：随手记下要做的事——交电费、还书、给老李回电话。能加、能划掉、能问还剩啥。
区别于"随口提醒"（带时间）和"家庭分工"（派给谁），这就是你自己的一张小清单。

本地持久化为干净 JSON，纯逻辑、可单测。
"""

from __future__ import annotations

import json
from pathlib import Path


def _norm(s) -> str:
    return (s or "").strip().lower()


class TodoList:
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

    def add(self, task) -> dict | None:
        task = (task or "").strip()
        if not task:
            return None
        for it in self.items:
            if _norm(it["task"]) == _norm(task) and not it["done"]:
                return it                       # 已有未办的同项，不重复加
        it = {"task": task, "done": False}
        self.items.append(it)
        self._save()
        return it

    def done(self, task) -> dict | None:
        n = _norm(task)
        for it in self.items:
            if not it["done"] and n and (n == _norm(it["task"]) or _norm(it["task"]) in n
                                         or n in _norm(it["task"])):
                it["done"] = True
                self._save()
                return it
        return None

    def pending(self) -> list:
        return [it["task"] for it in self.items if not it["done"]]

    def clear_done(self) -> int:
        k = len([it for it in self.items if it["done"]])
        self.items = [it for it in self.items if not it["done"]]
        self._save()
        return k

    def describe(self) -> str:
        p = self.pending()
        if not p:
            return "待办都清空啦，清爽。"
        return "还要做的：" + "、".join(p) + "。"

"""心愿与目标：记下长期想达成的事，能添、能记一笔进展、能销账，也能盘一盘。

既可记你的目标（让分身帮你盯着），也可存 TA 没了的"未了之事"。本地持久化、纯逻辑、可单测。
"""

from __future__ import annotations

import json
import time
from pathlib import Path


class GoalBook:
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

    def add(self, text, now=None) -> dict | None:
        text = (text or "").strip()
        if not text or any(g["text"] == text for g in self.items):
            return None if not text else next(g for g in self.items if g["text"] == text)
        g = {"text": text, "status": "open", "progress": [],
             "created": now if now is not None else time.time()}
        self.items.append(g)
        self._save()
        return g

    def _find(self, query):
        q = (query or "").strip()
        if not q:
            return None
        for g in self.items:
            if g["text"] == q or g["text"] in q or q in g["text"]:
                return g
        return None

    def note_progress(self, query, note) -> dict | None:
        g = self._find(query)
        note = (note or "").strip()
        if g is None or not note:
            return None
        g["progress"].append(note)
        self._save()
        return g

    def complete(self, query) -> dict | None:
        g = self._find(query)
        if g is None:
            return None
        g["status"] = "done"
        self._save()
        return g

    def open(self) -> list:
        return [g for g in self.items if g.get("status") != "done"]

    def done(self) -> list:
        return [g for g in self.items if g.get("status") == "done"]

    def summary(self) -> str:
        op, dn = self.open(), self.done()
        if not op and not dn:
            return "还没立下什么目标。想达成点什么，跟我说。"
        L = []
        if op:
            L.append("还想达成的：" + "、".join(g["text"] for g in op[:5]))
        if dn:
            L.append(f"已经做到的有 {len(dn)} 件，真好。")
        return " ".join(L)

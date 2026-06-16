"""采买清单：随口"买瓶酱油""把鸡蛋划掉"，分身替你记着一张购物/采买清单。

完全本地、持久化为干净 JSON。纯逻辑、零网络、可单测。每项可带数量与分类，能加、能划掉、能清。
"""

from __future__ import annotations

import json
from pathlib import Path


def _norm(name) -> str:
    return (name or "").strip().lower()


class ShoppingList:
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

    def add(self, name, qty=None, category=None) -> dict | None:
        name = (name or "").strip()
        if not name:
            return None
        for it in self.items:                       # 已有则累加/更新数量
            if _norm(it["name"]) == _norm(name):
                if qty:
                    it["qty"] = qty
                if category:
                    it["category"] = category
                self._save()
                return it
        it = {"name": name, "qty": qty, "category": category, "done": False}
        self.items.append(it)
        self._save()
        return it

    def check_off(self, name) -> dict | None:
        n = _norm(name)
        for it in self.items:
            if n and (n == _norm(it["name"]) or n in _norm(it["name"])):
                it["done"] = True
                self._save()
                return it
        return None

    def remove(self, name) -> bool:
        n = _norm(name)
        before = len(self.items)
        self.items = [it for it in self.items if not (n and n in _norm(it["name"]))]
        if len(self.items) != before:
            self._save()
            return True
        return False

    def pending(self) -> list:
        return [it for it in self.items if not it.get("done")]

    def clear(self) -> int:
        k = len(self.items)
        self.items = []
        self._save()
        return k

    def describe(self) -> str:
        p = self.pending()
        if not p:
            return "采买清单是空的。"
        parts = []
        for it in p:
            s = it["name"]
            if it.get("qty"):
                s += f"×{it['qty']}"
            parts.append(s)
        return "要买的：" + "、".join(parts) + "。"

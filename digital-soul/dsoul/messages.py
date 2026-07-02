"""捎个话：一家人住一块儿，难免有话要带——"等小明回来，跟他说妈喊他吃饭"。
分身替你记着，等那个人露面，主动把话捎到。本地持久化为干净 JSON，纯逻辑、可单测。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class Messages:
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

    def leave(self, to, text, frm="", now=None) -> dict | None:
        to = (to or "").strip()
        text = (text or "").strip()
        if not to or not text:
            return None
        it = {"to": to, "text": text, "from": (frm or "").strip(),
              "ts": (now or datetime.now()).strftime("%Y-%m-%d %H:%M"), "delivered": False}
        self.items.append(it)
        self._save()
        return it

    def pending_for(self, name) -> list:
        n = (name or "").strip()
        return [it for it in self.items
                if not it["delivered"] and n and (it["to"] in n or n in it["to"])]

    def deliver(self, name) -> list:
        """把攒给这人的话捎到，标记已带，返回一句句捎话。"""
        out = []
        for it in self.pending_for(name):
            it["delivered"] = True
            frm = f"{it['from']}" if it.get("from") else "有人"
            out.append(f"{frm}让我捎句话给你：「{it['text']}」")
        if out:
            self._save()
        return out

    def describe(self) -> str:
        pend = [it for it in self.items if not it["delivered"]]
        if not pend:
            return "没有要捎的话。"
        return "还没捎到的话：" + "；".join(
            f"给{it['to']}（{it['text']}）" for it in pend) + "。"

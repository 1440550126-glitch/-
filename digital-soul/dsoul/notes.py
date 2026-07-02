"""速记便签：随口一句"记个事——明天买菜"就存下来，回头能翻、能搜、能清。

完全本地、持久化为干净 JSON。纯逻辑、零网络、可单测。区别于"记忆库"(RAG)与"日程"(带日期)，
便签就是最轻的待办/备忘，不做语义检索、不做提醒，只图随手记、随手看。
"""

from __future__ import annotations

import json
import time
from pathlib import Path


class NoteBook:
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
        if not text:
            return None
        note = {"text": text, "ts": now if now is not None else time.time()}
        self.items.append(note)
        self._save()
        return note

    def recent(self, n=8) -> list:
        return [it["text"] for it in self.items[-n:][::-1]]

    def search(self, query, n=8) -> list:
        q = (query or "").strip()
        if not q:
            return []
        return [it["text"] for it in self.items if q in it["text"]][-n:][::-1]

    def clear(self) -> int:
        k = len(self.items)
        self.items = []
        self._save()
        return k

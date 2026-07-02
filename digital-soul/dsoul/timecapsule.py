"""时光胶囊：把一句话封存给未来——到某个日子，再由分身替 TA 交给某位家人。

比如"给孙女 18 岁生日的话""等你结婚那天再看"。完全本地、持久化为干净 JSON，
到点（含错过补送）才开封一次，开过即标记，不重复。纯逻辑、可单测。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .calendar_book import _DATE_FULL, _DATE_MD, normalize_date


def is_due(deliver_date, now) -> bool:
    """到开封日了吗？全日期：今天 >= 该日（错过也补送）；MM-DD：每年那天。"""
    if not deliver_date:
        return False
    if _DATE_FULL.match(deliver_date):
        return now.strftime("%Y-%m-%d") >= deliver_date
    if _DATE_MD.match(deliver_date):
        return now.strftime("%m-%d") == deliver_date
    return False


class CapsuleBook:
    """持久化的时光胶囊本。"""

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

    def add(self, recipient, deliver_date, message) -> dict | None:
        d = normalize_date(deliver_date)
        recipient = (recipient or "").strip()
        message = (message or "").strip()
        if not d or not message:
            return None
        cap = {"recipient": recipient or "你", "date": d, "message": message, "delivered": False}
        self.items.append(cap)
        self._save()
        return cap

    def pending(self) -> list:
        return [c for c in self.items if not c.get("delivered")]

    def due(self, now=None) -> list:
        """到点且未开封的胶囊；返回的同时标记为已开封（只送一次）。"""
        now = now or datetime.now()
        out, changed = [], False
        for c in self.items:
            if not c.get("delivered") and is_due(c.get("date"), now):
                c["delivered"] = True
                changed = True
                out.append(c)
        if changed:
            self._save()
        return out

    @staticmethod
    def speak(cap) -> str:
        """把一枚开封的胶囊说成一句郑重的交付。"""
        who = cap.get("recipient", "你")
        return f"{who}，有句话我一直存到今天才说给你听：「{cap.get('message', '')}」"

"""重要联系人：记着该记的号码——孩子、医生、邻居、急救。要紧时刻喊一声就找得到。
本地持久化为干净 JSON，可由 config/contacts.yaml 播种。纯逻辑、可单测。
"""

from __future__ import annotations

import json
from pathlib import Path

# 哪些关系算"紧急可找"
_URGENT = ("孩子", "儿子", "女儿", "闺女", "子女", "医生", "急救", "120", "社区", "邻居",
           "老伴", "老婆", "老公")


class ContactBook:
    def __init__(self, path, seed=None) -> None:
        self.path = Path(path)
        self.items: list[dict] = []
        self._load()
        if not self.items and seed:
            for c in (seed.get("contacts") if isinstance(seed, dict) else seed) or []:
                if isinstance(c, dict) and c.get("name"):
                    self.add(c.get("name"), c.get("phone", ""),
                             relation=c.get("relation", ""), note=c.get("note", ""))

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

    def add(self, name, phone="", relation="", note="") -> dict | None:
        name = (name or "").strip()
        if not name:
            return None
        it = {"name": name, "phone": str(phone or "").strip(),
              "relation": (relation or "").strip(), "note": (note or "").strip()}
        for i, c in enumerate(self.items):
            if c["name"] == name:
                self.items[i] = it
                self._save()
                return it
        self.items.append(it)
        self._save()
        return it

    def find(self, query):
        """按名字或关系找联系人（名字长的优先）。"""
        q = str(query or "")
        if not q:
            return None
        for c in sorted(self.items, key=lambda x: -len(x["name"])):
            if (c["name"] and c["name"] in q) or (c["relation"] and c["relation"] in q):
                return c
        return None

    def emergency_contacts(self) -> list:
        """要紧时能找的人（子女/医生/邻居/急救…）。"""
        return [c for c in self.items
                if any(u in (c["relation"] + c["name"]) for u in _URGENT)]

    def emergency_line(self) -> str:
        ec = self.emergency_contacts()
        if not ec:
            return ""
        return "、".join(f"{c['relation'] or c['name']}{('（' + c['phone'] + '）') if c['phone'] else ''}"
                        for c in ec[:3])

    def describe(self) -> str:
        if not self.items:
            return "还没记下要紧的联系人。"
        return "记着的电话：" + "、".join(
            f"{c['name']}{('（' + c['relation'] + '）') if c['relation'] else ''}{('：' + c['phone']) if c['phone'] else ''}"
            for c in self.items) + "。"

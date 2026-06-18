"""家庭共享·分工板：一家人的活儿派一派——今天谁买菜、谁接孩子、谁做饭。
分身替全家记着分工，谁来了提醒谁，也能报"今天的安排"。本地持久化，纯逻辑、可单测。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

# 常见家务（用于从"今天小明买菜"里认出活儿）
CHORES = ("买菜", "做饭", "做晚饭", "接孩子", "送孩子", "打扫", "拖地", "洗碗", "洗衣服",
          "倒垃圾", "取快递", "交水电费", "交物业费", "遛狗", "浇花", "陪老人", "缴费",
          "做家务", "采购", "接娃", "送娃")


class FamilyBoard:
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

    def assign(self, what, who="", when="今天", now=None) -> dict | None:
        what = (what or "").strip()
        if not what:
            return None
        it = {"what": what, "who": (who or "").strip(), "when": (when or "今天").strip(),
              "done": False, "ts": (now or datetime.now()).strftime("%Y-%m-%d %H:%M")}
        self.items.append(it)
        self._save()
        return it

    def pending(self) -> list:
        return [it for it in self.items if not it["done"]]

    def for_member(self, name) -> list:
        n = (name or "").strip()
        return [it for it in self.pending() if it["who"] and n and (it["who"] in n or n in it["who"])]

    def today(self) -> list:
        return [it for it in self.pending() if "今天" in it["when"] or not it["when"]]

    @staticmethod
    def _what_hit(what, q) -> bool:
        if not what:
            return False
        if what in q:
            return True
        return any(what[i:i + 2] in q for i in range(len(what) - 1))   # 共享两字片段也算

    def done(self, query) -> dict | None:
        q = str(query or "")
        for it in self.pending():
            if self._what_hit(it["what"], q) or (it["who"] and it["who"] in q):
                it["done"] = True
                self._save()
                return it
        return None

    def describe(self) -> str:
        pend = self.pending()
        if not pend:
            return "今天没派什么活儿，清闲。"
        return "今天的分工：" + "；".join(
            (f"{it['who']}—{it['what']}" if it["who"] else it["what"]) for it in pend) + "。"

"""常联系：好久没给谁打电话了，分身替你记着、提醒一句——别让亲情淡了。
config 里配谁、多久联系一次；说一声"给闺女打过电话了"就记上。本地持久化，纯逻辑、可单测。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path


def _today(now=None):
    return (now or datetime.now()).date()


class TouchLog:
    def __init__(self, path, seed=None) -> None:
        self.path = Path(path)
        self.people: dict = {}     # name -> {relation, every, last}
        self._load()
        if not self.people and seed:
            for p in (seed.get("people") if isinstance(seed, dict) else seed) or []:
                if isinstance(p, dict) and p.get("name"):
                    self.add(p["name"], p.get("every_days", 7), p.get("relation", ""))

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

    def add(self, name, every_days=7, relation="") -> dict | None:
        name = (name or "").strip()
        if not name:
            return None
        try:
            every = max(1, int(every_days))
        except (TypeError, ValueError):
            every = 7
        rec = self.people.setdefault(name, {"relation": "", "every": every, "last": None})
        rec["every"] = every
        if relation:
            rec["relation"] = relation.strip()
        self._save()
        return rec

    def _find(self, query):
        q = str(query or "")
        for name, rec in self.people.items():
            if (name and name in q) or (rec.get("relation") and rec["relation"] in q):
                return name
        return None

    def touched(self, query, now=None) -> str | None:
        name = self._find(query)
        if not name:
            return None
        self.people[name]["last"] = _today(now).isoformat()
        self._save()
        return name

    def overdue(self, now=None) -> list:
        """该联系的人：[(name, 距上次天数 or None), ...]，越久越靠前。"""
        today = _today(now)
        out = []
        for name, rec in self.people.items():
            last = rec.get("last")
            if last is None:
                out.append((name, None))
                continue
            try:
                d = date.fromisoformat(last)
            except ValueError:
                out.append((name, None))
                continue
            gap = (today - d).days
            if today >= d + timedelta(days=rec["every"]):
                out.append((name, gap))
        out.sort(key=lambda t: (-1 if t[1] is None else -t[1]))
        return out

    def reminders(self, now=None) -> str:
        od = self.overdue(now)
        if not od:
            return ""
        bits = []
        for name, gap in od[:3]:
            rec = self.people[name]
            who = f"{rec['relation']}{name}" if rec.get("relation") else name
            when = "好久没联系了" if gap is None else f"{gap}天没联系了"
            bits.append(f"{who}{when}")
        return "记得抽空联系一下：" + "；".join(bits) + "，别让亲情淡了。"

    def describe(self) -> str:
        if not self.people:
            return "还没记下要常联系的人。"
        return "常联系名单：" + "、".join(
            f"{r['relation'] or n}（{r['every']}天）" for n, r in self.people.items()) + "。"

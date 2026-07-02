"""养花：屋里那几盆花草，分身替你记着几天浇一次水，到点提醒一句，别旱着也别涝着。
本地持久化为干净 JSON，可由 config/plants.yaml 播种。纯逻辑、可单测。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path


def _today(now=None):
    return (now or datetime.now()).date()


class PlantBook:
    def __init__(self, path, seed=None) -> None:
        self.path = Path(path)
        self.plants: list[dict] = []
        self._load()
        if not self.plants and seed:
            for p in (seed.get("plants") if isinstance(seed, dict) else seed) or []:
                if isinstance(p, dict) and p.get("name"):
                    self.add(p["name"], p.get("water_every_days", 3), p.get("note", ""))

    def _load(self) -> None:
        if self.path.exists():
            try:
                self.plants = json.loads(self.path.read_text(encoding="utf-8")).get("plants", [])
            except Exception:
                self.plants = []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"plants": self.plants}, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    def add(self, name, every_days=3, note="") -> dict | None:
        name = (name or "").strip()
        if not name:
            return None
        try:
            every = max(1, int(every_days))
        except (TypeError, ValueError):
            every = 3
        p = {"name": name, "every": every, "note": (note or "").strip(), "last": None}
        for i, x in enumerate(self.plants):
            if x["name"] == name:
                p["last"] = x.get("last")
                self.plants[i] = p
                self._save()
                return p
        self.plants.append(p)
        self._save()
        return p

    def _find(self, name):
        for p in self.plants:
            if p["name"] and (p["name"] in str(name) or str(name) in p["name"]):
                return p
        return None

    def water(self, name, now=None) -> dict | None:
        p = self._find(name)
        if not p:
            return None
        p["last"] = _today(now).isoformat()
        self._save()
        return p

    def due(self, now=None) -> list:
        """该浇水的花：从没浇过的，或离上次浇水满了周期的。"""
        today = _today(now)
        out = []
        for p in self.plants:
            last = p.get("last")
            if last is None:
                out.append(p["name"])
                continue
            try:
                d = date.fromisoformat(last)
            except ValueError:
                out.append(p["name"])
                continue
            if today >= d + timedelta(days=p["every"]):
                out.append(p["name"])
        return out

    def reminders(self, now=None) -> str:
        due = self.due(now)
        return (f"该给{'、'.join(due)}浇水了，别旱着。") if due else ""

    def describe(self) -> str:
        if not self.plants:
            return "还没记下养的花草。"
        return "养着的花草：" + "、".join(
            f"{p['name']}（{p['every']}天一浇）" for p in self.plants) + "。"

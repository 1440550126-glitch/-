"""养宠：家里的猫猫狗狗，分身替你记着——几点喂、该遛了没，到点提醒，别饿着小家伙。
本地持久化为干净 JSON，可由 config/pets.yaml 播种。纯逻辑、可单测。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path


def _hhmm(s):
    try:
        h, m = str(s).split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return None


class PetBook:
    def __init__(self, path, seed=None) -> None:
        self.path = Path(path)
        self.pets: list[dict] = []
        self.fed_log: list[dict] = []      # [{name, ts}]
        self.walk_log: list[dict] = []     # [{name, date}]
        self._load()
        if not self.pets and seed:
            for p in (seed.get("pets") if isinstance(seed, dict) else seed) or []:
                if isinstance(p, dict) and p.get("name"):
                    self.add(p["name"], p.get("kind", ""), p.get("feed_times"),
                             p.get("walk", False), p.get("note", ""))

    def _load(self) -> None:
        if self.path.exists():
            try:
                d = json.loads(self.path.read_text(encoding="utf-8"))
                self.pets = d.get("pets", [])
                self.fed_log = d.get("fed_log", [])
                self.walk_log = d.get("walk_log", [])
            except Exception:
                self.pets, self.fed_log, self.walk_log = [], [], []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(
            {"pets": self.pets, "fed_log": self.fed_log, "walk_log": self.walk_log},
            ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, name, kind="", feed_times=None, walk=False, note="") -> dict | None:
        name = (name or "").strip()
        if not name:
            return None
        pet = {"name": name, "kind": (kind or "").strip(),
               "feed_times": [t for t in (feed_times or []) if _hhmm(t) is not None],
               "walk": bool(walk), "note": (note or "").strip()}
        for i, p in enumerate(self.pets):
            if p["name"] == name:
                self.pets[i] = pet
                self._save()
                return pet
        self.pets.append(pet)
        self._save()
        return pet

    def _find(self, name):
        for p in self.pets:
            if p["name"] and (p["name"] in str(name) or str(name) in p["name"]):
                return p
        return None

    def fed(self, name, now=None) -> dict | None:
        p = self._find(name)
        if not p:
            return None
        self.fed_log.append({"name": p["name"], "ts": (now or datetime.now()).strftime("%Y-%m-%d %H:%M")})
        self._save()
        return p

    def walked(self, name, now=None) -> dict | None:
        p = self._find(name)
        if not p:
            return None
        self.walk_log.append({"name": p["name"], "date": (date.today() if now is None else
                              (now.date() if hasattr(now, "date") else date.today())).isoformat()})
        self._save()
        return p

    def _fed_count(self, name, day) -> int:
        return sum(1 for r in self.fed_log if r["name"] == name and r["ts"][:10] == day)

    def due_feeding(self, now=None, window=45) -> list:
        now = now or datetime.now()
        cur = now.hour * 60 + now.minute
        day = now.strftime("%Y-%m-%d")
        out = []
        for p in self.pets:
            slots = [t for t in p.get("feed_times", []) if _hhmm(t) is not None]
            if not any(abs(cur - _hhmm(t)) <= window for t in slots):
                continue
            should = sum(1 for t in slots if _hhmm(t) <= cur + window)
            if self._fed_count(p["name"], day) < should:
                out.append(p["name"])
        return out

    def needs_walk(self, name, now=None) -> bool:
        p = self._find(name)
        if not p or not p.get("walk"):
            return False
        today = (date.today() if now is None else
                 (now.date() if hasattr(now, "date") else date.today())).isoformat()
        return not any(r["name"] == p["name"] and r["date"] == today for r in self.walk_log)

    def reminders(self, now=None) -> str:
        bits = []
        feed = self.due_feeding(now)
        if feed:
            bits.append(f"该喂{'、'.join(feed)}了")
        for p in self.pets:
            if p.get("walk") and self.needs_walk(p["name"], now):
                bits.append(f"该遛{p['name']}了")
        return ("，".join(bits) + "，别忘了小家伙。") if bits else ""

    def describe(self) -> str:
        if not self.pets:
            return "家里还没养宠物。"
        return "家里的小家伙：" + "、".join(
            f"{p['name']}（{p['kind']}）" if p["kind"] else p["name"] for p in self.pets) + "。"

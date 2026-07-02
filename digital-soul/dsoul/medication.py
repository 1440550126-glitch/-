"""用药守护：比"到点提醒"更进一步——记着每种药几点吃、吃了没、还剩多少、该不该续配。
像家里最上心的那个人，盯着你按时吃药、快没了提前张罗。

本地持久化为干净 JSON，可由 config/medications.yaml 播种。纯逻辑、可单测。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

_REFILL_THRESHOLD = 5      # 剩余剂量少于这个数就提醒续药


def _hhmm(s):
    try:
        h, m = str(s).split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return None


class MedBook:
    def __init__(self, path, seed=None) -> None:
        self.path = Path(path)
        self.meds: list[dict] = []
        self.log: list[dict] = []          # 服药记录 [{name, ts}]
        self._load()
        if not self.meds and seed:
            for m in (seed.get("meds") if isinstance(seed, dict) else seed) or []:
                if isinstance(m, dict) and m.get("name"):
                    self.add(m["name"], times=m.get("times"), note=m.get("note", ""),
                             stock=m.get("stock"), per_dose=m.get("per_dose", 1))

    def _load(self) -> None:
        if self.path.exists():
            try:
                d = json.loads(self.path.read_text(encoding="utf-8"))
                self.meds, self.log = d.get("meds", []), d.get("log", [])
            except Exception:
                self.meds, self.log = [], []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"meds": self.meds, "log": self.log},
                                        ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, name, times=None, note="", stock=None, per_dose=1) -> dict:
        name = (name or "").strip()
        times = [t for t in (times or []) if _hhmm(t) is not None]
        med = {"name": name, "times": times, "note": (note or "").strip(),
               "stock": stock, "per_dose": per_dose or 1}
        # 同名则更新
        for i, m in enumerate(self.meds):
            if m["name"] == name:
                self.meds[i] = med
                self._save()
                return med
        self.meds.append(med)
        self._save()
        return med

    def _taken_count(self, name, day) -> int:
        return sum(1 for r in self.log
                   if r["name"] == name and r["ts"][:10] == day)

    def taken_today(self, name, now=None) -> int:
        day = (now or datetime.now()).strftime("%Y-%m-%d")
        return self._taken_count(name, day)

    def take(self, name, now=None) -> dict | None:
        """记一次服药，并扣库存。"""
        now = now or datetime.now()
        for m in self.meds:
            if m["name"] == name or (name and name in m["name"]):
                self.log.append({"name": m["name"], "ts": now.strftime("%Y-%m-%d %H:%M")})
                if isinstance(m.get("stock"), (int, float)):
                    m["stock"] = max(0, m["stock"] - (m.get("per_dose") or 1))
                self._save()
                return m
        return None

    def due(self, now=None, window=45) -> list:
        """此刻该吃、但今天在这个点还没吃的药：[(name, time, note), ...]。"""
        now = now or datetime.now()
        cur = now.hour * 60 + now.minute
        day = now.strftime("%Y-%m-%d")
        out = []
        for m in self.meds:
            slots = [t for t in m.get("times", []) if _hhmm(t) is not None]
            due_slots = [t for t in slots if abs(cur - _hhmm(t)) <= window]
            if not due_slots:
                continue
            # 今天已吃次数 >= 到这个点该吃的次数，就算吃过了
            should = sum(1 for t in slots if _hhmm(t) <= cur + window)
            if self._taken_count(m["name"], day) < should:
                out.append((m["name"], due_slots[0], m.get("note", "")))
        return out

    def refill_alerts(self, threshold=_REFILL_THRESHOLD) -> list:
        """快吃完的药：[(name, stock), ...]。"""
        out = []
        for m in self.meds:
            s = m.get("stock")
            if isinstance(s, (int, float)) and s <= threshold:
                out.append((m["name"], int(s)))
        return out

    def reminders(self, now=None) -> list:
        """汇总此刻要说的话：到点提醒 + 续药提醒。"""
        lines = []
        for name, t, note in self.due(now):
            tip = f"（{note}）" if note else ""
            lines.append(f"该吃{name}了{tip}，{t} 这顿别忘了。")
        for name, stock in self.refill_alerts():
            lines.append(f"{name}只剩{stock}次的量了，记得早点去配。")
        return lines

    def describe(self) -> str:
        if not self.meds:
            return "还没记着要吃的药。"
        parts = []
        for m in self.meds:
            t = "/".join(m.get("times", [])) or "按需"
            stock = f"，剩{m['stock']}" if isinstance(m.get("stock"), (int, float)) else ""
            parts.append(f"{m['name']}（{t}{stock}）")
        return "在吃的药：" + "、".join(parts) + "。"

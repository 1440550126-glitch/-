"""习惯养成陪练：陪你戒烟、早睡、锻炼、喝水——每天打个卡，连了多少天、断了再续，
像个不唠叨却一直在的伙伴，给你鼓劲。本地持久化，纯逻辑、可单测。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

_MILES = {3: "三天", 7: "一周", 14: "两周", 21: "三周", 30: "一个月",
          50: "五十天", 100: "一百天", 365: "一整年"}


def _today(now=None):
    return (now or datetime.now()).date()


class HabitBook:
    def __init__(self, path, seed=None) -> None:
        self.path = Path(path)
        self.habits: dict = {}      # name -> {target, streak, last, total}
        self._load()
        if not self.habits and seed:
            for h in (seed.get("habits") if isinstance(seed, dict) else seed) or []:
                if isinstance(h, dict) and h.get("name"):
                    self.add(h["name"], h.get("target", ""))
                elif isinstance(h, str):
                    self.add(h)

    def _load(self) -> None:
        if self.path.exists():
            try:
                self.habits = json.loads(self.path.read_text(encoding="utf-8")).get("habits", {})
            except Exception:
                self.habits = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"habits": self.habits}, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    def add(self, name, target="") -> dict | None:
        name = (name or "").strip()
        if not name:
            return None
        h = self.habits.setdefault(name, {"target": "", "streak": 0, "last": None, "total": 0})
        if target:
            h["target"] = target.strip()
        self._save()
        return h

    def _find(self, name):
        if name in self.habits:
            return name
        for n in self.habits:
            if n and (n in str(name) or str(name) in n):
                return n
        return None

    def check_in(self, name, now=None) -> dict | None:
        key = self._find(name) or (self.add(name) and name)
        if key is None:
            return None
        h = self.habits[key]
        today = _today(now)
        if h["last"] == today.isoformat():
            return h                                     # 今天已打过
        if h["last"] == (today - timedelta(days=1)).isoformat():
            h["streak"] += 1
        else:
            h["streak"] = 1
        h["last"] = today.isoformat()
        h["total"] += 1
        self._save()
        return h

    def streak(self, name) -> int:
        key = self._find(name)
        return self.habits[key]["streak"] if key else 0

    def done_today(self, name, now=None) -> bool:
        key = self._find(name)
        return bool(key and self.habits[key]["last"] == _today(now).isoformat())

    def pending(self, now=None) -> list:
        return [n for n in self.habits if not self.done_today(n, now)]

    def encourage(self, name) -> str:
        key = self._find(name)
        if not key:
            return ""
        s = self.habits[key]["streak"]
        if s <= 0:
            return f"{key}，今天打个卡呗，万事开头难。"
        if s == 1:
            return f"{key}第一天，好的开始！明天接着来。"
        m = _MILES.get(s)
        if m:
            return f"{key}连续{s}天了，整整{m}，太棒了，给你点个大赞！"
        return f"{key}连续{s}天了，保持住，别断了哈。"

    def describe(self) -> str:
        if not self.habits:
            return "还没立什么小目标，想养成啥好习惯，我陪你。"
        parts = [f"{n}（连续{h['streak']}天）" for n, h in self.habits.items()]
        return "在坚持的：" + "、".join(parts) + "。"

"""本地日程本：记下家里的大事小事（生日、复诊、纪念日、约定），到点能提醒、能报。

完全本地、持久化为一个干净的 JSON；日期支持 "YYYY-MM-DD" 与 "MM-DD"（每年循环，如生日）。
纯逻辑、零网络、可单测。喂给晨间关怀简报当"今天打算/今天有什么事"。
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

_DATE_FULL = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_MD = re.compile(r"^\d{2}-\d{2}$")


def normalize_date(s) -> str | None:
    """把 '2026-06-16' / '06-16' / '6/16' / '6月16日' 规整成标准串；非法返回 None。"""
    if not s:
        return None
    t = str(s).strip().replace("/", "-")
    m = re.match(r"^(\d{1,4})年(\d{1,2})月(\d{1,2})日?$", t)
    if m:
        y, mo, d = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    m = re.match(r"^(\d{1,2})月(\d{1,2})日?$", t)
    if m:
        mo, d = m.groups()
        return f"{int(mo):02d}-{int(d):02d}"
    parts = t.split("-")
    try:
        if len(parts) == 3:
            return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        if len(parts) == 2:
            return f"{int(parts[0]):02d}-{int(parts[1]):02d}"
    except ValueError:
        return None
    return None


def _md(date_str) -> str:
    return date_str[-5:] if date_str else ""


def occurs_on(event_date, now) -> bool:
    """事件是否落在 now 这天（全日期按年月日，MM-DD 按每年循环）。"""
    if not event_date:
        return False
    today_full = now.strftime("%Y-%m-%d")
    if _DATE_FULL.match(event_date):
        return event_date == today_full
    if _DATE_MD.match(event_date):
        return event_date == now.strftime("%m-%d")
    return False


def days_until(event_date, now) -> int | None:
    """距离下一次发生还有几天（今天=0）；非法返回 None。"""
    if not event_date:
        return None
    if _DATE_FULL.match(event_date):
        try:
            d = datetime.strptime(event_date, "%Y-%m-%d").date()
        except ValueError:
            return None
        return (d - now.date()).days
    if _DATE_MD.match(event_date):
        mo, da = int(event_date[:2]), int(event_date[3:])
        for yr in (now.year, now.year + 1):
            try:
                d = datetime(yr, mo, da).date()
            except ValueError:
                return None
            if d >= now.date():
                return (d - now.date()).days
    return None


class EventBook:
    """持久化的本地日程本。"""

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

    def add(self, title, date, kind="事") -> dict | None:
        d = normalize_date(date)
        title = (title or "").strip()
        if not d or not title:
            return None
        ev = {"title": title, "date": d, "kind": kind}
        if ev not in self.items:
            self.items.append(ev)
            self._save()
        return ev

    def today(self, now=None) -> list:
        now = now or datetime.now()
        return [e for e in self.items if occurs_on(e.get("date"), now)]

    def upcoming(self, days=7, now=None) -> list:
        now = now or datetime.now()
        out = []
        for e in self.items:
            n = days_until(e.get("date"), now)
            if n is not None and 0 <= n <= days:
                out.append((n, e))
        return [e for _, e in sorted(out, key=lambda x: x[0])]

    def describe_today(self, now=None) -> list:
        return [f"{e['title']}" for e in self.today(now)]

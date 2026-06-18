"""就医/约定提醒：记着复诊、体检、办事的日子，提前张罗、临走叮嘱该带什么。
像家里那个把一家人日程都记在心里的人。本地持久化为 JSON，纯逻辑、可单测。
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

# 按事由提醒该带的东西
_PREP = {
    "复诊": "带上病历和医保卡，挂号别赶早高峰。",
    "体检": "记得空腹，前一晚别吃太油。",
    "看病": "带上医保卡和之前的检查单。",
    "打针": "带上医保卡，打完歇一会儿再走。",
}


def _parse(s):
    for fmt in ("%Y-%m-%d", "%m-%d"):
        try:
            d = datetime.strptime(str(s).strip(), fmt).date()
            return d.replace(year=date.today().year) if fmt == "%m-%d" else d
        except ValueError:
            continue
    return None


class AppointmentBook:
    def __init__(self, path, seed=None) -> None:
        self.path = Path(path)
        self.items: list[dict] = []
        self._load()
        if not self.items and seed:
            for a in (seed.get("appointments") if isinstance(seed, dict) else seed) or []:
                if isinstance(a, dict) and a.get("date"):
                    self.add(a.get("date"), a.get("what", ""), a.get("where", ""),
                             a.get("note", ""))

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

    def add(self, when, what="", where="", note="") -> dict | None:
        d = _parse(when)
        if d is None:
            return None
        it = {"date": d.isoformat(), "what": (what or "").strip(),
              "where": (where or "").strip(), "note": (note or "").strip()}
        self.items.append(it)
        self.items.sort(key=lambda x: x["date"])
        self._save()
        return it

    def upcoming(self, now=None, within=14) -> list:
        """近 within 天内的安排：[(days_left, item), ...]。"""
        today = (now or datetime.now()).date()
        out = []
        for it in self.items:
            d = _parse(it["date"])
            if d is None:
                continue
            left = (d - today).days
            if 0 <= left <= within:
                out.append((left, it))
        return sorted(out, key=lambda t: t[0])

    def _prep_for(self, what) -> str:
        for key, tip in _PREP.items():
            if key in (what or ""):
                return tip
        return ""

    def reminders(self, now=None, within=3) -> list:
        """临近的事提前提醒一句（含该带什么）。"""
        lines = []
        for left, it in self.upcoming(now, within):
            when = "今天" if left == 0 else ("明天" if left == 1 else f"还有{left}天")
            head = f"{when}有安排：{it['what'] or '一件事'}"
            if it.get("where"):
                head += f"（{it['where']}）"
            prep = it.get("note") or self._prep_for(it["what"])
            lines.append(head + "。" + (prep if prep else ""))
        return lines

    def describe(self) -> str:
        up = self.upcoming(within=30)
        if not up:
            return "近一个月没排什么事。"
        return "近期安排：" + "；".join(
            f"{it['date']} {it['what']}" for _, it in up) + "。"

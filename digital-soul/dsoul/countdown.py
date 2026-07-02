"""倒计时：惦记着要紧的日子——离过年、离退休、离娃高考、离你回来还有几天。
配在 config/countdown.yaml，或随口"记一下，十月一号是去旅行"。本地持久化，纯逻辑、可单测。
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

_ZH = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
       "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
_MD = re.compile(r"([零〇一二两三四五六七八九十\d]+)\s*月\s*([零〇一二两三四五六七八九十\d]+)\s*[日号]")


def _zh2num(s):
    if s.isdigit():
        return int(s)
    if s in _ZH:
        return _ZH[s]
    if s.startswith("十"):
        return 10 + (_ZH.get(s[1:], 0) if len(s) > 1 else 0)
    if s.endswith("十"):
        return _ZH.get(s[0], 1) * 10
    if "十" in s:
        a, b = s.split("十", 1)
        return _ZH.get(a, 1) * 10 + _ZH.get(b, 0)
    return None


def parse_date(s):
    """'YYYY-MM-DD' / 'MM-DD' / 'X月X日' → (month, day, year|None)；解析不出 None。"""
    s = str(s or "").strip()
    parts = s.split("-")
    if all(p.strip().isdigit() for p in parts) and len(parts) in (2, 3):
        nums = [int(p) for p in parts]
        return (nums[1], nums[2], nums[0]) if len(nums) == 3 else (nums[0], nums[1], None)
    m = _MD.search(s)
    if m:
        mo, da = _zh2num(m.group(1)), _zh2num(m.group(2))
        if mo and da:
            return (mo, da, None)
    return None


def days_to(md, now=None):
    """到下一个该日期还有几天。md=(month, day, year|None)。"""
    if not md:
        return None
    now = now or datetime.now()
    today = now.date()
    month, day, year = md
    try:
        target = date(year, month, day) if year else date(today.year, month, day)
    except ValueError:
        return None
    if not year and target < today:
        try:
            target = date(today.year + 1, month, day)
        except ValueError:
            return None
    return (target - today).days


class CountdownBook:
    def __init__(self, path, seed=None) -> None:
        self.path = Path(path)
        self.items: list[dict] = []
        self._load()
        if not self.items and seed:
            src = seed.get("dates") if isinstance(seed, dict) else seed
            if isinstance(src, dict):
                for name, d in src.items():
                    self.add(name, d)
            elif isinstance(src, list):
                for it in src:
                    if isinstance(it, dict) and it.get("name") and it.get("date"):
                        self.add(it["name"], it["date"])

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

    def add(self, name, when) -> dict | None:
        name = str(name or "").strip()
        md = parse_date(when)
        if not name or not md:
            return None
        it = {"name": name, "date": str(when).strip(),
              "md": [md[0], md[1]] + ([md[2]] if md[2] else [])}
        self.items = [x for x in self.items if x["name"] != name] + [it]
        self._save()
        return it

    def _md_of(self, it):
        m = it.get("md") or []
        return (m[0], m[1], m[2] if len(m) > 2 else None) if len(m) >= 2 else None

    def days_for(self, name, now=None):
        for it in self.items:
            if it["name"] and (it["name"] in str(name) or str(name) in it["name"]):
                return days_to(self._md_of(it), now)
        return None

    def upcoming(self, now=None, within=400) -> list:
        out = []
        for it in self.items:
            d = days_to(self._md_of(it), now)
            if d is not None and 0 <= d <= within:
                out.append((it["name"], d))
        return sorted(out, key=lambda t: t[1])

    def describe(self, name, now=None) -> str:
        d = self.days_for(name, now)
        if d is None:
            return f"我还没记下「{name}」是哪天，你说一声我记上。"
        if d == 0:
            return f"就是今天！「{name}」到了。"
        return f"离「{name}」还有 {d} 天。"

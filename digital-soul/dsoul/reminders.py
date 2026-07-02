"""随口提醒：你说"提醒我下午三点吃药""半小时后叫我关火"，分身记下，到点提醒。
比 YAML 定时自动化更随意、口语。本地持久化，纯逻辑、可单测。
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

_REL_MIN = re.compile(r"(\d+)\s*分钟后")
_REL_HR = re.compile(r"(\d+)\s*个?小时后")
_CLOCK = re.compile(r"(上午|下午|晚上|早上|中午|凌晨)?\s*(\d{1,2})\s*点\s*(半|\d{1,2}\s*分)?")

_ZH = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
       "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
_ZH_CLOCK = re.compile(r"([零〇一二两三四五六七八九十]+)\s*(点|分)")


def _zh2num(s):
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


def normalize_clock(u):
    """把"三点""八点半"这类中文数字时刻转成阿拉伯数字，方便统一解析。"""
    def _rep(m):
        n = _zh2num(m.group(1))
        return (str(n) if n is not None else m.group(1)) + m.group(2)
    return _ZH_CLOCK.sub(_rep, str(u or ""))


def parse_when(utterance, now=None):
    """从口语里解析出提醒时间；解析不出返回 None。"""
    u = normalize_clock(utterance)
    now = now or datetime.now()
    if "半小时后" in u:
        return now + timedelta(minutes=30)
    m = _REL_MIN.search(u)
    if m:
        return now + timedelta(minutes=int(m.group(1)))
    m = _REL_HR.search(u)
    if m:
        return now + timedelta(hours=int(m.group(1)))
    day = now
    if "明天" in u:
        day = now + timedelta(days=1)
    elif "后天" in u:
        day = now + timedelta(days=2)
    m = _CLOCK.search(u)
    if m:
        ampm, hh, mm = m.group(1), int(m.group(2)), m.group(3)
        if ampm in ("下午", "晚上") and hh < 12:
            hh += 12
        elif ampm == "中午" and hh < 12:
            hh = 12
        minute = 30 if mm == "半" else (int(mm.replace("分", "").strip()) if mm else 0)
        cand = day.replace(hour=hh % 24, minute=minute % 60, second=0, microsecond=0)
        if cand <= now and "明天" not in u and "后天" not in u:
            cand += timedelta(days=1)
        return cand
    return None


def extract_task(utterance):
    """把"提醒我X"里的 X（要提醒的事）抠出来。"""
    u = normalize_clock(utterance)
    for lead in ("记得提醒我", "提醒我", "到点叫我", "叫我"):
        if lead in u:
            u = u[u.find(lead) + len(lead):]
            break
    # 去掉时间词，留住事
    u = _CLOCK.sub("", u)
    for t in ("半小时后", "明天", "后天", "今天"):
        u = u.replace(t, "")
    u = _REL_MIN.sub("", u)
    u = _REL_HR.sub("", u)
    return u.strip("，,。.：: 　去要该的")


def is_reminder_request(utterance) -> bool:
    u = utterance or ""
    if "提醒" in u or "到点叫我" in u:
        return True
    # "半小时后叫我关火""三点叫我"这类：有"叫我"且带时间词
    return "叫我" in u and any(k in u for k in ("后", "点", "明天", "后天", "半小时"))


class ReminderBook:
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

    def add(self, task, at_dt) -> dict | None:
        task = (task or "").strip()
        if not task or at_dt is None:
            return None
        it = {"task": task, "at": at_dt.strftime("%Y-%m-%d %H:%M"), "fired": False}
        self.items.append(it)
        self.items.sort(key=lambda x: x["at"])
        self._save()
        return it

    def parse_and_add(self, utterance, now=None) -> dict | None:
        when = parse_when(utterance, now)
        task = extract_task(utterance)
        return self.add(task, when) if (when and task) else None

    def due(self, now=None) -> list:
        now = now or datetime.now()
        stamp = now.strftime("%Y-%m-%d %H:%M")
        out = []
        for it in self.items:
            if not it["fired"] and it["at"] <= stamp:
                it["fired"] = True
                out.append(it["task"])
        if out:
            self._save()
        return out

    def pending(self) -> list:
        return [it for it in self.items if not it["fired"]]

    def describe(self) -> str:
        p = self.pending()
        if not p:
            return "没有待提醒的事。"
        return "记着要提醒你的：" + "；".join(f"{it['at'][5:]} {it['task']}" for it in p) + "。"

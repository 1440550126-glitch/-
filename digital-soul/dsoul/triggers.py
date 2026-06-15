"""自动化触发：定时（"每天22点提醒锁门"）+ 条件（"我一进门就开灯"）。

把一句话解析成触发器（时间 / 事件 + 动作），持久化到 JSON；
由 daemon 的定时回合与 presence 的进门事件来"点火"。动作可为：设备 / 场景 / 提醒。
解析为纯函数、可单测。
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

from .devices import parse_device_command

_ENTER = ("进门", "一进", "回到家", "到家", "回家")


def _action_desc(a: dict) -> str:
    t = a.get("type")
    if t == "remind":
        return f"提醒：{a['text']}"
    if t == "scene":
        return f"场景：{a['name']}"
    if t == "device":
        v = f" {a['val']}" if a.get("val") is not None else ""
        return f"设备：{a['device']} {a['act']}{v}"
    return "?"


def _parse_action(text: str, scene_names):
    if "提醒" in text:
        tail = text.split("提醒", 1)[1].strip(" ：:，,。.我")
        return {"type": "remind", "text": tail or "（到点了）"}
    for s in (scene_names or []):
        if s in text:
            return {"type": "scene", "name": s}
    cmd = parse_device_command(text)
    if cmd:
        return {"type": "device", "device": cmd[0], "act": cmd[1], "val": cmd[2]}
    return None


def parse_trigger(text: str, scene_names=None):
    """识别自动化指令。返回 {kind, spec, action, desc} 或 None。"""
    text = text or ""
    action = _parse_action(text, scene_names)
    if action is None:
        return None
    m = re.search(r"(\d{1,2})\s*[:：点]\s*(\d{1,2})?", text)
    if m and any(w in text for w in ("每天", "点", ":", "：", "定时", "到")):
        hh, mm = int(m.group(1)), int(m.group(2) or 0)
        if 0 <= hh < 24 and 0 <= mm < 60:
            return {"kind": "time", "spec": f"{hh:02d}:{mm:02d}", "action": action,
                    "desc": f"每天 {hh:02d}:{mm:02d} → {_action_desc(action)}"}
    if any(w in text for w in _ENTER):
        return {"kind": "event", "spec": "enter", "action": action,
                "desc": f"一进门 → {_action_desc(action)}"}
    return None


class TriggerBook:
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
        self.path.write_text(
            json.dumps({"items": self.items}, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, trig: dict) -> dict:
        tid = hashlib.sha1((trig.get("desc", "") + str(time.time())).encode("utf-8")).hexdigest()[:12]
        item = {"id": tid, "last_fired": None, **trig}
        self.items.append(item)
        self._save()
        return item

    def all(self):
        return list(self.items)

    def time_triggers(self):
        return [t for t in self.items if t.get("kind") == "time"]

    def event_triggers(self, spec):
        return [t for t in self.items if t.get("kind") == "event" and t.get("spec") == spec]

    def mark_fired(self, tid, day):
        for t in self.items:
            if t["id"] == tid:
                t["last_fired"] = day
                self._save()
                return

    def clear(self) -> int:
        n = len(self.items)
        self.items = []
        self._save()
        return n

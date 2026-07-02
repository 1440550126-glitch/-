"""体征记录：量了血压、血糖、体重、体温，说一声就替你记下，攒一摞、看趋势、异常提个醒。
不替代医生，只帮你把数攒着、看个走势。本地持久化，纯逻辑、可单测。
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

_KIND_KW = {
    "血压": ("血压", "高压", "低压"),
    "血糖": ("血糖",),
    "体温": ("体温", "发烧", "烧到"),
    "体重": ("体重", "称了", "几斤", "多少斤", "公斤"),
    "心率": ("心率", "脉搏", "心跳"),
}

_NUM = re.compile(r"\d+(?:\.\d+)?")


def detect_kind(utterance):
    u = utterance or ""
    for kind, kws in _KIND_KW.items():
        if any(k in u for k in kws):
            return kind
    return None


def _numbers(utterance):
    return [float(x) for x in _NUM.findall(str(utterance or ""))]


def flag(kind, value) -> str:
    """给个通俗的异常提醒（仅提示，不诊断）；正常或看不懂则空。"""
    nums = [float(x) for x in _NUM.findall(str(value))]
    if not nums:
        return ""
    if kind == "血压" and len(nums) >= 2:
        sys, dia = nums[0], nums[1]
        if sys >= 140 or dia >= 90:
            return "血压有点偏高，少盐、别累着，要是常这样就去复查。"
        if sys < 90 or dia < 60:
            return "血压偏低，起身慢点、别猛站，多喝水。"
        return ""
    if kind == "血糖":
        v = nums[0]
        if v >= 7.0:
            return "血糖偏高，少吃甜的和主食，饭后走一走。"
        if v < 3.9:
            return "血糖偏低，赶紧吃块糖或点东西，别硬扛。"
        return ""
    if kind == "体温":
        v = nums[0]
        if v >= 37.3:
            return "有点发烧，多喝温水、好好歇着，烧得高就去医院。"
        return ""
    if kind == "心率":
        v = nums[0]
        if v >= 100:
            return "心跳有点快，坐下歇会儿，深呼吸。"
        if v < 50:
            return "心跳偏慢，要是头晕不适就别大意，去查查。"
    return ""


class VitalsLog:
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

    def record(self, kind, value, now=None) -> dict | None:
        kind = (kind or "").strip()
        value = str(value or "").strip()
        if not kind or not value:
            return None
        it = {"kind": kind, "value": value,
              "ts": (now or datetime.now()).strftime("%Y-%m-%d %H:%M")}
        self.items.append(it)
        self._save()
        return it

    def parse_and_record(self, utterance, now=None) -> dict | None:
        kind = detect_kind(utterance)
        if not kind:
            return None
        nums = _NUM.findall(str(utterance or ""))
        if not nums:
            return None
        value = f"{nums[0]}/{nums[1]}" if (kind == "血压" and len(nums) >= 2) else nums[0]
        return self.record(kind, value, now)

    def latest(self, kind):
        for it in reversed(self.items):
            if it["kind"] == kind:
                return it
        return None

    def recent(self, kind, k=5) -> list:
        out = [it for it in self.items if it["kind"] == kind]
        return out[-k:][::-1]

    def describe(self, kind=None) -> str:
        if kind:
            r = self.recent(kind, 5)
            if not r:
                return f"还没记过{kind}。"
            return f"近几次{kind}：" + "、".join(f"{it['value']}({it['ts'][5:10]})" for it in r) + "。"
        if not self.items:
            return "还没记过体征。"
        kinds = sorted({it["kind"] for it in self.items})
        return "记着的体征：" + "、".join(kinds) + "。想看哪项的趋势？"

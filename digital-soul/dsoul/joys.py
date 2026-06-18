"""小确幸日记：像家里那个爱往好处想的人，晚上问一句"今天有啥开心的事"，
把你说的好事记下来；日子久了，翻出来念给你听，提醒你日子其实挺甜。

本地持久化为干净 JSON，纯逻辑、可单测。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

_JOY_MARK = ("开心", "高兴", "不错", "顺利", "幸福", "满足", "美", "舒服", "值了",
             "暖心", "好玩", "乐", "圆满", "顺心")
_NEG = ("不开心", "不高兴", "不顺", "不舒服", "没意思")


def is_sharing_joy(utterance) -> bool:
    """像是在分享一件开心事（含正向词、且不是反着说、不是疑问）。"""
    u = (utterance or "").strip()
    if not u or u.endswith(("吗", "吗？", "?", "？")):
        return False
    if any(n in u for n in _NEG):
        return False
    return any(k in u for k in _JOY_MARK)


def _gist(utterance) -> str:
    """去掉口头开头，留住好事的主干。"""
    u = (utterance or "").strip()
    for pre in ("今天", "我今天", "跟你说", "告诉你", "哎", "嘿", "其实"):
        if u.startswith(pre):
            u = u[len(pre):].lstrip("，, 　")
    return u.strip("。.！!～~ ")


class JoyLog:
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

    def add(self, text, who="", now=None) -> dict | None:
        text = _gist(text)
        if not text:
            return None
        now = now or datetime.now()
        it = {"text": text, "who": (who or "").strip(), "ts": now.strftime("%Y-%m-%d %H:%M")}
        self.items.append(it)
        self._save()
        return it

    def recent(self, k=3) -> list:
        return [it["text"] for it in self.items[-k:]][::-1]

    def count(self) -> int:
        return len(self.items)

    def reflect(self, k=3) -> str:
        """把最近的开心事念给你听。"""
        rs = self.recent(k)
        if not rs:
            return "还没记下什么开心事呢，今天有啥乐子，说给我听听？"
        return "这阵子这些事让你开心过——" + "；".join(rs) + "。你看，日子其实挺甜的。"

    def acknowledge(self, text="") -> str:
        """记下一件开心事后，暖暖地回应一句。"""
        g = _gist(text)
        return (f"「{g}」——这事真好，我替你记下了，留着以后慢慢回味。" if g
                else "真好，我替你记下了。")


def evening_prompt(now=None) -> str:
    """傍晚到夜里，主动问一句今天的好事（不在此时段返回空）。"""
    h = (now or datetime.now()).hour
    if 18 <= h <= 23:
        return "今天有什么开心的小事吗？说给我听听，我帮你记着。"
    return ""

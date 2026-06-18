"""找东西：上年纪了爱忘事——钥匙、老花镜、存折放哪了？说一声"我把X放在Y了"它记着，
"X放哪了"它告诉你。本地持久化，纯逻辑、可单测。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_VERB = "(?:放在|放到|搁在|搁到|收在|摆在|塞在|放|搁)"
# "我把钥匙放在鞋柜上了" / "存折搁抽屉里" / "老花镜放茶几上"
_PUT_BA = re.compile(r"把\s*(.+?)\s*" + _VERB + r"\s*(.+)")
_PUT_PLAIN = re.compile(r"^(?:我)?\s*(.+?)\s*" + _VERB + r"\s*(.+)")
# "钥匙放哪了" / "我的老花镜呢" / "存折在哪"
_WHERE = re.compile(r"(?:我的)?\s*(.+?)\s*(?:放哪|搁哪|在哪|哪儿去了|呢|找不到|不见了)")

_PUT_HINT = ("放在", "放到", "搁在", "搁到", "收在", "摆在", "塞在", "放", "搁")
_WHERE_HINT = ("放哪", "搁哪", "在哪", "哪儿去", "呢", "找不到", "不见了")


def _clean_place(p):
    p = (p or "").strip("的了 ")
    return p.rstrip("了上里中")        # 去掉"鞋柜上""抽屉里"的方位尾字


def parse_put(utterance):
    """从"我把X放在Y了"里抽出 (东西, 地方)。"""
    u = str(utterance or "").strip().strip("。.！!，, ")
    if not any(h in u for h in _PUT_HINT):
        return None
    m = _PUT_BA.search(u) or _PUT_PLAIN.search(u)
    if not m:
        return None
    item = m.group(1).strip("我刚才把 ")
    place = _clean_place(m.group(2))
    return (item, place) if item and place else None


def parse_where(utterance):
    """从"X放哪了"里抽出要找的东西。"""
    u = str(utterance or "").strip().strip("。.？?！!，, ")
    if not any(h in u for h in _WHERE_HINT):
        return None
    m = _WHERE.search(u)
    if not m:
        return None
    item = m.group(1).strip("我的刚才 ")
    if item in ("你", "我", "他", "她", "它", "咱", "谁", "啥", "什么", "人家"):
        return None                              # "你呢"这类不是找东西
    return item or None


class Belongings:
    def __init__(self, path, seed=None) -> None:
        self.path = Path(path)
        self.items: dict = {}      # 东西 -> {place, ts}
        self._load()
        if not self.items and isinstance(seed, dict):
            for k, v in (seed.get("places") or {}).items():
                self.put(k, v)

    def _load(self) -> None:
        if self.path.exists():
            try:
                self.items = json.loads(self.path.read_text(encoding="utf-8")).get("items", {})
            except Exception:
                self.items = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"items": self.items}, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    def put(self, item, place) -> dict | None:
        item, place = (item or "").strip(), (place or "").strip()
        if not item or not place:
            return None
        self.items[item] = {"place": place}
        self._save()
        return {"item": item, "place": place}

    def where(self, item):
        item = (item or "").strip()
        if item in self.items:
            return self.items[item]["place"]
        for k, v in self.items.items():     # 模糊：钥匙 ~ 车钥匙
            if k and (k in item or item in k):
                return v["place"]
        return None

    def describe(self) -> str:
        if not self.items:
            return "还没记下啥东西搁哪了。"
        return "我替你记着的：" + "、".join(f"{k}在{v['place']}" for k, v in self.items.items()) + "。"

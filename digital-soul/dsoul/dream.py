"""梦境生成：睡眠时把记忆碎片 + 情绪 + 纠缠联想重组成一段梦。

如同大脑在睡眠中重放并重组记忆——这里用"纠缠扩散"把相关记忆串起来，
按当下主导情绪上色，拼成一段超现实的梦。有大模型则让它编织得更自然。
纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import time
from pathlib import Path

from .entangle import spreading_activation

_CONNECTORS = ["梦里，", "然后场景一转，", "忽然，", "不知怎么，", "接着，", "梦的最后，"]
_MOOD_TINT = {
    "喜": "梦是暖色的，", "怒": "梦里有些躁动，", "哀": "梦里有点潮湿发冷，",
    "惧": "梦里影影绰绰，", "爱": "梦很温柔，", "恶": "梦里有点别扭，", "欲": "梦里在找一个人，",
}


def _fragment(text: str) -> str:
    parts = re.split(r"[，。；,.!！?？—…]", text or "")
    return next((p.strip() for p in parts if p.strip()), text or "")[:24]


def compose_dream(items, mood=None, names=None, llm=None, seed=None, extra=None) -> str:
    items = [it for it in items if "dream" not in (it.get("tags") or [])]
    if len(items) < 2:
        return ""
    rng = random.Random(seed)
    pool = sorted(items, key=lambda it: it.get("created", 0), reverse=True)[:8] or items
    seeds = rng.sample(pool, min(2, len(pool)))
    chain = list(seeds)
    for _w, it in spreading_activation(seeds, items, names=names, k=3):
        chain.append(it)
    if extra:                                  # 白天反复冒出的心声也飘进梦里
        chain += [{"text": e} for e in extra if e]
    if llm is not None and getattr(llm, "available", False):
        woven = _llm_dream(llm, chain, mood)
        if woven:
            return woven
    out = _MOOD_TINT.get(mood, "")
    for i, it in enumerate(chain[:4]):
        out += _CONNECTORS[i % len(_CONNECTORS)] + _fragment(it.get("text", "")) + "。"
    return out.strip()


def _llm_dream(llm, chain, mood) -> str:
    frags = "；".join(it.get("text", "")[:30] for it in chain)
    system = ("你在做梦。把下面这些记忆碎片编织成一小段超现实、跳跃、朦胧的梦境，"
              "三四句话、第一人称，不要解释，只写梦本身。")
    try:
        return llm.chat(system, f"记忆碎片：{frags}；梦的底色情绪：{mood or '平静'}").strip()
    except Exception:
        return ""


class DreamLog:
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
        self.path.write_text(json.dumps({"items": self.items}, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, text: str, mood=None):
        if not text:
            return None
        rec = {"id": hashlib.sha1((text + str(time.time())).encode("utf-8")).hexdigest()[:12],
               "text": text, "mood": mood, "ts": time.time()}
        self.items.append(rec)
        self.items = self.items[-30:]
        self._save()
        return rec

    def recent(self, k: int = 3):
        return self.items[-k:][::-1]

"""好奇心：分身对世界的求知欲——遇到陌生的就发问、攒成待解的疑问，找机会问回来。

把"我想了解这个世界"落成机制：从听到的话里挑出记忆里没见过的词/事（陌生），
形成第一人称的好奇提问，存进疑问本；之后可主动问主人，学到了就销账。
纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from .reflect import _bigrams

_TEMPLATES = ["你说的「{t}」，是什么呀？我有点好奇。",
              "「{t}」是怎么回事？我还不太懂。",
              "你为什么会提到「{t}」呢？背后有故事吗？"]
# 没信息量的常见二元组，不值得好奇
_COMMON = {"最近", "今天", "昨天", "明天", "现在", "有点", "觉得", "非常", "真的", "什么",
           "这个", "那个", "一个", "一下", "知道", "可能", "应该", "还是", "已经", "时候",
           "迷上", "开始", "打算", "喜欢", "想要"}


def novel_terms(text: str, known_blob: str):
    """text 里出现、但已知记忆里从没见过的显著二元组（=陌生的事物）。"""
    out = []
    for w in sorted(set(_bigrams(text or ""))):          # 排序保证确定性
        if w not in (known_blob or "") and w not in _COMMON and w not in out:
            out.append(w)
    return out[:3]


def form_questions(text: str, known_blob: str):
    """把陌生事物变成好奇的提问：[(问题, 词), …]。"""
    qs = []
    for i, t in enumerate(novel_terms(text, known_blob)):
        qs.append((_TEMPLATES[i % len(_TEMPLATES)].format(t=t), t))
    return qs


class QuestionLog:
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

    def add(self, term: str, q: str):
        if any(it["term"] == term for it in self.items):       # 同一件事不重复好奇
            return None
        rec = {"id": hashlib.sha1((term + str(time.time())).encode("utf-8")).hexdigest()[:12],
               "term": term, "q": q, "asked": False, "ts": time.time()}
        self.items.append(rec)
        self.items = self.items[-50:]
        self._save()
        return rec

    def open(self):
        return [it for it in self.items if not it.get("asked")]

    def mark_asked(self, qid: str):
        for it in self.items:
            if it["id"] == qid:
                it["asked"] = True
                self._save()
                return

    def resolve_known(self, known_blob: str) -> int:
        """学到了就销账：疑问里的词如今已出现在记忆里，则移除。"""
        before = len(self.items)
        self.items = [it for it in self.items if it["term"] not in (known_blob or "")]
        if len(self.items) != before:
            self._save()
        return before - len(self.items)

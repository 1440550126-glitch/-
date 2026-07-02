"""生平导入：把逝者/某人的聊天记录、书信，变成「TA 的记忆」与口头禅。

聊天记录里挑出 TA 本人说的话 → 一条条第一人称记忆；再统计高频短语，
作为口头禅 / 语气词的候选（喂给 identity，让分身更像 TA）。纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

import re
from collections import Counter

from .reflect import _bigrams


def parse_chatlog(text: str, person: str) -> list[str]:
    """从聊天记录里取出 person 说过的话（支持可选的 [时间] 前缀）。"""
    if not text or not person:
        return []
    pat = re.compile(r"^(?:\[[^\]]*\]\s*)?" + re.escape(person) + r"\s*[:：]\s*(.+)$")
    out = []
    for ln in text.splitlines():
        m = pat.match(ln.strip())
        if m:
            msg = m.group(1).strip()
            if msg:
                out.append(msg)
    return out


def candidate_phrases(utterances, k: int = 8, min_count: int = 3) -> list[str]:
    """TA 反复说的高频短语 → 口头禅 / 语气候选。"""
    c: Counter = Counter()
    for u in utterances:
        c.update(set(_bigrams(u)))
    return [w for w, n in c.most_common() if n >= min_count][:k]

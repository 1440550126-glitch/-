"""编年生平 + 嘱托：把一生按年份串成故事；保管临终留言与家训，郑重交付给后人。

面向数字遗产——有些话，TA 想留给后人。config/legacy.yaml 配 last_words（嘱托/留言）与
precepts（家训）。chronicle 把带年份的记忆编年成第一人称生平。纯逻辑、零依赖、可单测。
"""

from __future__ import annotations


def chronicle(items) -> str:
    """把带年份的记忆编年成一段第一人称生平。无年份记忆则返回空。"""
    dated = []
    seen = set()
    for it in items or []:
        w = it.get("when")
        if not (w and str(w).isdigit()) or "dream" in (it.get("tags") or []):
            continue
        key = (int(w), it.get("text", ""))
        if key in seen:
            continue
        seen.add(key)
        dated.append(key)
    if not dated:
        return ""
    dated.sort(key=lambda x: x[0])
    body = " ".join(f"{y} 年，{t.rstrip('。.')}。" for y, t in dated)
    return "我这一生，捡几件记得的说说——" + body


def last_words(legacy) -> list:
    return list((legacy or {}).get("last_words") or [])


def precepts(legacy) -> list:
    return list((legacy or {}).get("precepts") or [])

"""感恩与遗憾：回望一生的记忆，挑出"最感念的"与"放不下的"。

按每条记忆被标注的情绪归类（喜/乐/爱 → 感恩；哀/恶 → 遗憾），各取最有分量的几条，
说成第一人称的一句话。纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

_GRATEFUL = {"喜", "乐", "爱"}
_REGRET = {"哀", "恶"}


def _texts(items, emotions):
    out = []
    for it in items or []:
        if it.get("emotion") in emotions:
            t = (it.get("text") or "").strip()
            if t and "（照片）" not in t and "dream" not in (it.get("tags") or []):
                out.append(t)
    return out


def gratitudes(items, k=3) -> list:
    return _texts(items, _GRATEFUL)[:k]


def regrets(items, k=3) -> list:
    return _texts(items, _REGRET)[:k]


def reflect(items) -> str:
    """把感恩与遗憾说成一小段第一人称的回望。"""
    g = gratitudes(items)
    r = regrets(items)
    if not g and not r:
        return "这一生啊，平平淡淡，倒也没什么大恨大怨，知足了。"
    L = []
    if g:
        L.append("我最感念的，是" + "、".join(x.rstrip("。.") for x in g) + "。")
    if r:
        L.append("要说放不下的，是" + "、".join(x.rstrip("。.") for x in r) + "——不过都过去了。")
    return " ".join(L)

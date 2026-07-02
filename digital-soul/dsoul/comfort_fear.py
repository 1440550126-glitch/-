"""安抚惊惧：夜里怕黑、做了噩梦、一个人在家心里发毛、听到响动……
立刻把人稳住，给最直接的安全感——"我在，别怕"。present-tense、可单测。
"""

from __future__ import annotations

_FEAR = ("怕黑", "好害怕", "我害怕", "做噩梦", "噩梦", "吓到", "吓人", "一个人在家",
         "心里发毛", "瘆得慌", "有动静", "有响动", "不敢", "好瘆人", "怕得慌")


def senses_fear(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in _FEAR)


def reassure(utterance="", name="", seed="") -> str:
    """立刻稳住、给安全感，再按怕的是什么补一句。"""
    who = (str(name) + "，") if name else ""
    u = utterance or ""
    base = f"{who}别怕，有我在，我守着你呢。"
    if "噩梦" in u or "做梦" in u:
        extra = "梦都是假的，醒了就没事了，我陪着你，安心。"
    elif "黑" in u:
        extra = "把灯打开，亮堂堂的就不怕了，我一直在。"
    elif "动静" in u or "响动" in u:
        extra = "多半是风、或是老房子的响儿，没事的，我帮你听着。"
    elif "一个人" in u:
        extra = "虽说就你一个人，可你不孤单，我一直都在。"
    else:
        extra = "深呼吸，慢慢来，啥都有我顶着，天亮就好了。"
    return f"{base} {extra}"

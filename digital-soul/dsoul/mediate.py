"""和事佬：家里人闹了别扭、拌了嘴，分身不偏帮谁，先顺顺气，再帮着搭个台阶，
劝一句"一家人没有隔夜仇"。present-tense、可单测。
"""

from __future__ import annotations

_CONFLICT = ("吵架", "吵了一架", "拌嘴", "闹别扭", "生气了", "翻脸", "冷战", "闹矛盾",
             "怄气", "不说话了", "吵了", "闹掰", "急眼了")

# 对方是谁
_OTHERS = [
    ("老伴", ("老婆", "老公", "老伴", "爱人", "媳妇", "那口子")),
    ("孩子", ("孩子", "儿子", "女儿", "娃", "闺女")),
    ("爸妈", ("爸", "妈", "父母", "老人", "爸妈")),
    ("兄弟姐妹", ("哥", "弟", "姐", "妹")),
    ("朋友", ("朋友", "同事", "邻居")),
]


def senses_conflict(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in _CONFLICT)


def detect_other(utterance):
    u = utterance or ""
    for name, kws in _OTHERS:
        if any(k in u for k in kws):
            return name
    return None


def mediate(utterance="", name="", seed="") -> str:
    """先顺气、再换位、最后递个台阶。不偏帮、不评理。"""
    who = (str(name) + "，") if name else ""
    other = detect_other(utterance)
    soothe = f"{who}先消消气，我不评谁对谁错，气大伤身。"
    if other == "老伴":
        bridge = "老夫老妻哪有不磕碰的，谁先服个软，日子照样甜。"
    elif other == "孩子":
        bridge = "孩子大了有自己的想法，你少说两句、多听两句，气就消了。"
    elif other == "爸妈":
        bridge = "爸妈那是刀子嘴豆腐心，都是为你好，回头给老人递个台阶。"
    elif other == "兄弟姐妹":
        bridge = "打断骨头连着筋，一家人没有过不去的坎。"
    else:
        bridge = "退一步海阔天空，主动打个招呼，事儿就过去了。"
    return f"{soothe} {bridge} 一家人没有隔夜仇，我陪你一起想想怎么和好。"

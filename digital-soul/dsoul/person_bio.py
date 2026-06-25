"""人物小传：把连到某个人的那些记忆，归纳成一段有温度的"人物志"。
打开 [[小婷]]，看见的不只是一串记忆链接，而是一段话：她是谁、我们怎么认识、
我答应过她什么、一起经历过什么、在我眼里她是什么样的人。

纯逻辑、可单测、不接大模型也能跑（按"承诺/相识/共同经历/印象"归类再串成段）；
接了本地大模型可以写得更顺，但这套规则保证：只用记忆里的事，不编造。
"""

from __future__ import annotations

import re

# 关系 → 称呼这个人时用的代词（把记忆里的人名换成"她/他"，读着像在讲 ta）
_SHE = ("老婆", "妻子", "媳妇", "妈", "母", "女儿", "闺女", "姐", "妹", "奶奶", "外婆",
        "姑", "姨", "婶", "嫂", "女")
_HE = ("老公", "丈夫", "爸", "父", "儿子", "哥", "弟", "爷爷", "外公", "叔", "舅", "伯", "男")

_PROMISE = ("答应", "保证", "说好", "一定", "许诺", "承诺")
_MILESTONE = ("认识", "相识", "结婚", "成家", "那年", "第一次", "出生", "生日", "毕业", "相遇")
_SHARED = ("一起", "我俩", "我们", "陪", "带她", "带他", "带着", "共同", "同甘共苦")
_TRAIT = ("话不多", "讲原则", "拿手", "脾气", "性子", "善良", "手巧", "能干", "要强", "嘴硬",
          "心软", "爱", "最", "总是", "从不", "做得一手", "极")
_YEAR = re.compile(r"(19|20)\d{2}\s*年?")


def pronoun(relation: str) -> str:
    r = str(relation or "")
    if any(k in r for k in _SHE):
        return "她"
    if any(k in r for k in _HE):
        return "他"
    return "ta"


def _cat(m: str) -> str:
    if any(k in m for k in _PROMISE):
        return "promise"
    if any(k in m for k in _MILESTONE) or _YEAR.search(m):
        return "milestone"
    if any(k in m for k in _SHARED):
        return "shared"
    if any(k in m for k in _TRAIT):
        return "trait"
    return "other"


def categorize(memories) -> dict:
    """把记忆按 相识/共同经历/承诺/印象/其它 归类（保序）。"""
    out = {"milestone": [], "shared": [], "promise": [], "trait": [], "other": []}
    seen = set()
    for m in (memories or []):
        m = str(m or "").strip()
        if not m or m in seen:
            continue
        seen.add(m)
        out[_cat(m)].append(m)
    return out


def _rw(m: str, name: str, pr: str) -> str:
    """记忆改写：把人名换成代词、收尾加句号；'我'开头保留（第一人称视角）。"""
    s = m.replace(name, pr).strip()
    # 称谓后面紧跟代词的收一收（"我爸他"→"我爸"、"老婆她"→"老婆"）
    s = re.sub(r"(爸|妈|哥|姐|弟|妹|爷|奶|公|婆|叔|姨|舅|伯|嫂|老婆|老公|丈夫|妻子)(她|他|ta)", r"\1", s)
    s = re.sub(r"[。.!！]+$", "", s)
    return s + "。"


_CLOSER = {
    "她": "这些点点滴滴，我都替她收着。",
    "他": "这些点点滴滴，我都替他记着。",
    "ta": "这些点点滴滴，我都记在心里。",
}


def compose_bio(name, relation="", memories=None) -> str:
    """从连到这个人的记忆，串一段小传。没有记忆就返回空（不硬写）。"""
    name = str(name).strip()
    mems = [str(m).strip() for m in (memories or []) if str(m).strip()]
    if not mems:
        return ""
    pr = pronoun(relation)
    cats = categorize(mems)
    lead = f"{name}是我的{relation}。" if relation else f"{name}，是我心里记挂的人。"
    parts = [lead]
    # 相识/里程碑 → 共同经历 → 承诺 → 印象 → 其它，读着像传记不像流水账
    for cat in ("milestone", "shared", "promise", "trait", "other"):
        for m in cats[cat]:
            parts.append(_rw(m, name, pr))
    parts.append(_CLOSER[pr])
    # 去重相邻、拼成一段
    seen, uniq = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return "".join(uniq)

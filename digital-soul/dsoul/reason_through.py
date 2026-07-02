"""想通一件事：碰上要拿主意、要表态的事，分身不脱口而出，而像人一样在心里掂量——
先有个初步念头，再转念想想另一面，连上自己的三观和过往，最后落定一个想法，
有时还"本来觉得…，转念一想…"。会犹豫、会改主意、会想通。纯逻辑、可单测。
"""

from __future__ import annotations

_DELIBERATE = ("该不该", "要不要", "值不值", "值得吗", "怎么办", "好不好", "对不对",
               "你说我", "我是不是该", "纠结", "两难", "拿不定主意", "拿不准", "选哪个",
               "怎么选", "该选")

# 常见两难的两面（话题词 → (一面之词, 另一面之词)）
_TWO_SIDES = [
    ("辞职", "辞了图个痛快、换种活法", "可饭碗要紧，骑驴找马更稳妥"),
    ("跳槽", "人往高处走，趁机会闯一闯", "可新东家未必更好，得打听清楚"),
    ("买房", "有套房，心里踏实", "可别让房贷把日子压垮了"),
    ("买车", "出行方便、有面子", "可养车也是一笔不小的开销"),
    ("借钱", "帮人是情分，能搭把手就搭", "可亲兄弟也得明算账，量力而行"),
    ("创业", "趁年轻闯一闯，不留遗憾", "可担子重、风险大，得想好退路"),
    ("吵架", "争一口气也是人之常情", "可都是家里人，退一步海阔天空"),
    ("催婚", "成家立业是正理，做长辈的着急", "可缘分急不来，还得看孩子自己"),
    ("搬家", "换个环境、图个新气象", "可故土难离，老邻居老街坊也舍不得"),
    ("分手", "不合适早做了断也好", "可在一起这些年的情分，别冲动"),
]


def is_dilemma(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in _DELIBERATE)


def detect_topic(utterance):
    u = utterance or ""
    for name, a, b in _TWO_SIDES:
        if name in u:
            return (name, a, b)
    return None


def reason_through(utterance, value=None, memory=None, mood=None, seed="") -> str:
    """走一遍想的过程：初念 → 转念 → 连上三观/过往 → 落定（谦逊、不替你拿主意）。"""
    s = str(seed or utterance or "")
    topic = detect_topic(utterance)
    parts = []
    if topic:
        _name, side_a, side_b = topic
        first, second = (side_a, side_b) if len(s) % 2 == 0 else (side_b, side_a)
        parts.append(f"这事吧，我头一个念头是——{first}。")
        parts.append(f"不过转念一想，{second}。")
    else:
        parts.append("这事不简单，我得好好想想。")
        parts.append("凡事都有两面，急着下结论容易偏。")
    if mood and mood not in ("平静", None):
        parts.append(f"（我这会儿心里有点{mood}，尽量想得周全些。）")
    if value:
        parts.append(f"我这人，最看重的是{value}。")
    if memory:
        parts.append(f"我也想起{str(memory).rstrip('。.')}。")
    parts.append("想来想去——大主意还得你自己拿；要我说，别慌、别只图一时痛快，"
                 "顺着良心、看长远些，多半错不了。")
    return " ".join(parts)

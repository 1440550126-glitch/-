"""对对子：老人爱跟孙辈玩对仗——"天对地，雨对风"。你出个字/词，它对上。
取自《笠翁对韵》等经典词对。纯逻辑、可单测。
"""

from __future__ import annotations

# 经典对仗（双向）。键值互为一对。
_PAIRS_RAW = {
    "天": "地", "雨": "风", "花": "叶", "山": "水", "日": "月", "云": "雾",
    "来": "去", "古": "今", "红": "绿", "高": "低", "长": "短", "春": "秋",
    "南": "北", "东": "西", "上": "下", "新": "旧", "晴": "雨", "江": "河",
    "明月": "清风", "大陆": "长空", "山花": "海树", "赤日": "苍穹",
    "三尺剑": "六钧弓", "桃红": "柳绿", "鸟语": "花香", "金乌": "玉兔",
}
_PAIRS = {}
for _a, _b in _PAIRS_RAW.items():
    _PAIRS[_a] = _b
    _PAIRS.setdefault(_b, _a)

_SAMPLE = ["天对地，雨对风，大陆对长空。", "来对往，密对稀，燕舞对莺啼。",
           "山对海，地对天，日月对山川。"]


def opposite(word):
    """给一个字/词，对出它的对仗；没有就返回 None。"""
    return _PAIRS.get(str(word or "").strip())


def is_couplet(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("对什么", "对啥", "对对子", "对个对子", "对下联", "对个下联",
                                "对子", "对对联"))


def respond(utterance) -> str:
    """从"天对什么"里取上字，对出下字；只说"对个对子"则给个范例。"""
    import re
    u = str(utterance or "")
    m = re.search(r"([一-鿿]{1,3})\s*对(?:什么|啥|个啥|什么好)", u)
    if m:
        w = m.group(1)
        opp = opposite(w)
        return f"{w}对{opp}。" if opp else f"{w}嘛……这个有点刁，你来对对看？"
    return _SAMPLE[len(u) % len(_SAMPLE)]

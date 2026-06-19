"""书法字体：楷书、行书、草书、隶书、篆书各是什么样、谁写得好。
看到一幅字、想练练毛笔字，能说出个门道。纯数据 + 纯逻辑、可单测。
"""

from __future__ import annotations

_SCRIPTS = {
    "楷书": "端端正正、一笔一画，最适合初学；‘欧颜柳赵’四大家（欧阳询、颜真卿、柳公权、赵孟頫）。",
    "行书": "比楷书流畅、又比草书好认，最实用；王羲之《兰亭序》号称‘天下第一行书’。",
    "草书": "笔画连绵、奔放洒脱，最难认；张旭、怀素被称‘草圣’，狂草最是淋漓。",
    "隶书": "蚕头燕尾、字形扁方，从篆书简化而来，汉代最盛行。",
    "篆书": "最古老的字体，分大篆、小篆；秦始皇统一文字用的就是小篆，线条圆转。",
    "行楷": "介于行书和楷书之间，既好看又好认，日常写字很合适。",
}

_ALIAS = {"正楷": "楷书", "真书": "楷书", "狂草": "草书", "小篆": "篆书", "大篆": "篆书",
          "毛笔字": "楷书"}

_FACTS = {
    "兰亭序": "王羲之的行书代表作，号称‘天下第一行书’。",
    "天下第一行书": "指王羲之的《兰亭序》。",
    "书圣": "指东晋的王羲之，书法登峰造极。",
    "草圣": "指唐代的张旭（也含怀素），擅狂草。",
    "颜筋柳骨": "形容颜真卿的字筋肉丰满、柳公权的字骨力遒劲。",
}


def _table(config) -> dict:
    db = dict(_SCRIPTS)
    if isinstance(config, dict) and isinstance(config.get("calligraphy"), dict):
        for k, v in config["calligraphy"].items():
            if str(v).strip():
                db[str(k)] = str(v).strip()
    return db


def scripts(config=None) -> list:
    return list(_table(config))


def find_script(query, config=None) -> str:
    u = str(query or "")
    db = _table(config)
    best, blen = "", 0
    for name in list(db) + list(_FACTS):
        if name in u and len(name) > blen:
            best, blen = name, len(name)
    for a, real in _ALIAS.items():
        if a in u and len(a) > blen and real in db:
            best, blen = real, len(a)
    return best


def about(query, config=None) -> str:
    db = _table(config)
    name = query if query in db else find_script(query, config)
    if name in db:
        return f"{name}：{db[name]}"
    if name in _FACTS:
        return f"{name}：{_FACTS[name]}"
    return ""


def four_masters() -> str:
    return "楷书四大家是：欧阳询、颜真卿、柳公权、赵孟頫（欧颜柳赵）。"


def is_calligraphy_query(utterance, config=None) -> bool:
    u = str(utterance or "")
    if any(k in u for k in ("书法", "毛笔字", "字体", "四大家", "练字")):
        return True
    if find_script(u, config) and any(k in u for k in ("是什么", "啥样", "什么样", "介绍",
                                                       "怎么写", "讲讲", "什么意思", "是谁")):
        return True
    return False

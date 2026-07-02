"""轻量标注：给记忆自动打"情感"标签、抽取"时间"，用于情感时间线。

纯规则、零依赖、中文友好。想更准可换成模型分类，但这套足够驱动时间线。
"""

from __future__ import annotations

import re

EMOJI = {
    "喜悦": "😊",
    "悲伤": "😢",
    "愤怒": "😠",
    "恐惧": "😨",
    "深情": "❤️",
    "怀念": "🕰️",
    "平静": "😐",
}

_LEXICON: dict[str, list[str]] = {
    "喜悦": ["开心", "高兴", "快乐", "喜欢", "幸福", "笑", "棒", "赞", "自豪",
            "骄傲", "享受", "温暖", "甜", "爽", "满足", "兴奋", "好玩"],
    "悲伤": ["难过", "伤心", "哭", "失去", "去世", "离世", "遗憾",
            "孤独", "心痛", "泪", "委屈", "失落", "想念", "思念"],
    "愤怒": ["生气", "愤怒", "讨厌", "恨", "烦", "可恶", "气死", "不爽"],
    "恐惧": ["害怕", "怕", "担心", "焦虑", "紧张", "恐惧", "不安"],
    "深情": ["最爱", "守护", "一辈子", "老婆", "亲爱", "在乎", "珍惜",
            "陪你", "陪我", "白头", "牵手"],
    "怀念": ["当年", "小时候", "以前", "曾经", "那时候", "怀念", "从小",
            "儿时", "那年", "记得"],
}


def classify_emotion(text: str) -> dict:
    """返回 {'label', 'score', 'scores'}；无任何命中则为"平静"。"""
    text = text or ""
    scores = {label: 0 for label in _LEXICON}
    for label, words in _LEXICON.items():
        for w in words:
            scores[label] += text.count(w)
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return {"label": "平静", "score": 0, "scores": scores}
    return {"label": best, "score": scores[best], "scores": scores}


_YEAR = re.compile(r"(?:19|20)\d{2}")


def extract_when(text: str) -> str | None:
    """从文本里抽一个粗粒度时间（年份）。抽不到返回 None。"""
    m = _YEAR.search(text or "")
    return m.group(0) if m else None

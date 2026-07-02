"""像人一样接话：听人说事，不只"哦"一声——顺着接一句、问一句，显出真在听、真上心。
听到"去了哪儿"问好不好玩，听到"见了谁"问人家近况，听到"在学什么"问难不难。

不是每句都追问（那样烦），只在对方分享、又没别的更要紧的事可接时，问一句。纯逻辑、可单测。
"""

from __future__ import annotations

# (识别正则/关键词, 追问模板)。按先后匹配，命中即返回。
_PATTERNS = [
    (("去了", "去过", "刚从", "回来"), "哦？那地方怎么样，玩得还开心吧？"),
    (("见了", "见到", "碰到", "遇到"), "是吗，他最近还好吧？"),
    (("买了", "新买", "添了"), "买啦，你喜欢就好，划算吗？"),
    (("在学", "学起", "报了班", "练"), "学这个呀，上手难不难？"),
    (("做了", "做的", "下厨", "炒了", "炖了"), "听着就香，味道怎么样？"),
    (("看了", "在追", "看的"), "好看吗？讲的啥呀？"),
    (("最近在", "这阵子", "忙着"), "忙得过来吗？别太累着。"),
    (("生病", "感冒", "不舒服", "住院"), "哎，要紧不？好好养着，缺啥跟我说。"),
]

# 像是在"分享一件事"（陈述句），而不是提问/命令
_QUESTION_END = ("吗", "吗？", "?", "？", "呢", "呢？", "吧", "吧？")


def is_sharing(utterance) -> bool:
    """像不像在跟我分享一件事（有内容、不是提问、不是太短）。"""
    u = (utterance or "").strip()
    if len(u) < 4 or u.endswith(_QUESTION_END):
        return False
    return any(any(k in u for k in kws) for kws, _q in _PATTERNS)


def followup(utterance) -> str:
    """顺着对方的话，问一句感兴趣的。没合适的可问就空。"""
    u = utterance or ""
    if u.strip().endswith(_QUESTION_END):
        return ""
    for kws, q in _PATTERNS:
        if any(k in u for k in kws):
            return q
    return ""


def generic_followup(seed="") -> str:
    """实在没具体可问的，给句通用的捧场，让话头能接下去。"""
    opts = ["嗯，后来呢？跟我细说说。", "是吗，我听着呢，你接着讲。", "哦？还有呢？"]
    return opts[len(str(seed)) % len(opts)]

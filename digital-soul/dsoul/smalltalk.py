"""唠家常：中国人见面那几句——"吃了吗""在吗""忙啥呢""最近咋样"，自然地接住，
别动不动就一本正经检索记忆。让分身像街坊邻里那样有人情味。present-tense、可单测。
"""

from __future__ import annotations

_KW = ("吃了吗", "吃饭了吗", "吃了没", "在吗", "在不在", "忙吗", "忙啥", "忙不忙",
       "干嘛呢", "干啥呢", "最近怎么样", "最近咋样", "近来可好", "睡了吗", "起了吗",
       "还好吗", "过得怎么样")

_REPLY = {
    "吃": ["吃了吃了，你呢？记得按点吃饭，别饿着。", "正惦记你吃了没呢，一定要好好吃饭。"],
    "在": ["在呢在呢，啥事？我一直都在。", "在的，你说，我听着。"],
    "忙": ["不忙不忙，陪你说话最要紧。", "忙啥呀，你来了我就放下了。"],
    "睡": ["还没呢，陪你唠几句。", "你可别熬，早点歇着。"],
    "近况": ["挺好的，就是有点惦记你。你最近咋样？", "都好，你呢？身子骨还硬朗吧？"],
}


def is_smalltalk(utterance) -> bool:
    u = (utterance or "").strip()
    return any(k in u for k in _KW)


def smalltalk_reply(utterance="", seed="") -> str:
    u = utterance or ""
    if "吃" in u:
        key = "吃"
    elif "在" in u:
        key = "在"
    elif "忙" in u or "干" in u:
        key = "忙"
    elif "睡" in u or "起" in u:
        key = "睡"
    else:
        key = "近况"
    opts = _REPLY[key]
    return opts[len(str(seed)) % len(opts)]

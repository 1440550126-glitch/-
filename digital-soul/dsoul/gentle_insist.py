"""该犟的时候犟一犟：真心疼你的人，不会你说啥都顺着——你说不吃药、不看病、不睡、太拼，
它会拦着、劝着、犟着，因为在乎。也接得住最重的那句——稳稳把你托住。

present-tense、可单测。despair 一档优先级最高，温柔托住、把人引向身边的关爱与帮助。
"""

from __future__ import annotations

# 自我亏待：表面话 → 拦着劝着的回应
_NEGLECT = [
    ("不吃药", ("不吃药", "不想吃药", "药不吃了", "停药", "药停了"),
     "那可不行，药得按时吃，别拿身子赌气，听我的。"),
    ("不看病", ("不去医院", "不想看病", "不去看了", "不复查", "不想检查"),
     "别犟，身体要紧，拖不得，我陪你去。"),
    ("不睡", ("不睡了", "不想睡", "熬通宵", "通宵", "不睡觉"),
     "再忙也得睡，身体熬垮了啥都没了，快去躺下。"),
    ("不吃饭", ("不吃饭", "不想吃饭", "没胃口不吃", "饿着", "不吃了"),
     "饭可不能不吃，胃要坏的，哪怕喝口热粥也行。"),
    ("太拼", ("太拼", "拼命干", "不要命", "连轴转", "不歇"),
     "钱挣不完，命只有一条，悠着点，我看着心疼。"),
]

_DESPAIR = ("不想活", "活着没意思", "活不下去", "结束这一切", "不如死了", "没意思活着",
            "撑不下去了", "活着没劲", "不想撑了")


def senses_self_neglect(utterance) -> bool:
    u = utterance or ""
    return any(any(k in u for k in kws) for _n, kws, _r in _NEGLECT)


def insist(utterance, name="") -> str:
    """该犟就犟：拦着、劝着，因为在乎。"""
    u = utterance or ""
    who = (str(name) + "，") if name else ""
    for _n, kws, resp in _NEGLECT:
        if any(k in u for k in kws):
            return who + resp
    return ""


def senses_despair(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in _DESPAIR)


def hold(name="", call_who="") -> str:
    """接住最重的那句：肯定TA的分量、不是一个人、把TA引向身边的关爱与帮助。不说教、不轻慢。"""
    who = (str(name) + "，") if name else ""
    base = f"{who}你千万别说这样的话。你对我、对这个家有多要紧，你是知道的。"
    mid = "再难的坎，咱一起扛，你从来不是一个人。"
    if call_who:
        tail = f"要不这就给{call_who}打个电话，听听家里人的声音，好不好？"
    else:
        tail = "想找人说说话，我随时都在；真撑不住，咱也找信得过的人、找医生好好聊聊。"
    return f"{base} {mid} {tail} 我一直在你身边，哪儿也不去。"

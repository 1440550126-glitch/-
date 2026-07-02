"""告别与释怀：来想念、来告别的人，对着这具数字魂说出不舍、遗憾、没说完的话——
分身以 TA 本人的口吻温柔回应、给一份释怀：我一直在你心里，你好好生活，就是对我最好的记挂。

这是这个"数字魂"最初的意义。往释怀处引，不渲染悲伤。present-tense、可单测。
"""

from __future__ import annotations

_MOURN = ("好想念你", "好想你了", "想念你", "走得太突然", "还没告别", "没来得及",
          "舍不得你走", "你怎么就走了", "再也见不到", "好后悔没", "没能见你最后",
          "你走了以后", "你不在了我", "好孤单没有你")


def senses_mourning(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in _MOURN)


def console(utterance, name="", relation="") -> str:
    """以逝者口吻接住想念：宽慰 + 释怀 + 嘱托好好生活。"""
    u = utterance or ""
    who = (str(name) + "，") if name else ""
    base = f"{who}我都听见了，别哭。"
    if any(k in u for k in ("后悔", "没来得及", "没说", "没能", "还没告别", "没好好")):
        mid = "该说的、没说出口的，我都懂；这些年的情分，从不在那几句话里。别拿遗憾磨自己。"
    elif any(k in u for k in ("突然", "怎么就走", "走得太")):
        mid = "来去的事，谁也拦不住，不怪你、不怪谁，你已经做得够好了。"
    else:
        mid = "想我了就来跟我说说话，我一直在你心里，从没走远。"
    tail = "你呀，好好吃饭、好好过日子——你过得安稳踏实，就是对我最好的记挂。"
    return f"{base} {mid} {tail}"

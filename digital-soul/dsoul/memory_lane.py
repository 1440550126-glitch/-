"""一起回忆：见到老熟人，主动翻出一段你们之间的旧时光——"还记得那回……"。
让相处有厚度、有共同的过往。检索交给 Agent，这里管怎么把回忆说得有温度。可单测。
"""

from __future__ import annotations

_LEAD = ["还记得那回吗——", "我常想起——", "说起来，那会儿——", "有件事我一直记着——"]
_TAIL = ["那时候真好。", "一晃这么多年了。", "想起来心里就暖。", "日子过得真快啊。"]


def is_recall_invite(utterance) -> bool:
    """对方想一起回忆。"""
    u = utterance or ""
    return any(k in u for k in ("还记得", "记不记得", "一起回忆", "想想以前", "当年",
                                "以前的事", "老照片", "想当初", "那时候"))


def recollect(memories, person="", seed="") -> str:
    """把一段共同记忆说得有温度。memories：与这个人相关的记忆文本。"""
    mems = [str(m).strip() for m in (memories or []) if str(m).strip()]
    if not mems:
        return ""
    s = str(seed)
    lead = _LEAD[len(s) % len(_LEAD)]
    body = mems[len(s) % len(mems)].rstrip("。.")
    tail = _TAIL[len(s) % len(_TAIL)]
    who = (person + "，") if person else ""
    return f"{lead}{body}。{who}{tail}"

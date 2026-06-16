"""触景生情 / 睹物思人：给一个由头（一个词、一样东西、一个地方），
顺着相关记忆与当时的情绪，说一段带着温度的回想。纯逻辑、可单测。

Agent.reminisce_about() 负责检索记忆与情绪后调用本模块。
"""

from __future__ import annotations

_LEAD = {
    "喜": "想起来还是忍不住笑",
    "乐": "想起来还是忍不住笑",
    "哀": "想起来心里就发软",
    "爱": "那是我心头最暖的一块",
    "惧": "当时是真有点怕",
    "怒": "那会儿还真有点来气",
    "恶": "想起来还有点不是滋味",
    "欲": "到现在还惦记着",
}


def reminisce(cue, memories, emotion=None) -> str:
    """cue：由头；memories：相关记忆文本列表；emotion：当时的主导情绪（七情之一）。"""
    cue = (cue or "这个").strip() or "这个"
    mems = [str(m).strip() for m in (memories or []) if str(m).strip()]
    if not mems:
        return f"说起{cue}，我一时竟想不真切，可那点感觉还在心里。"
    lead = _LEAD.get(emotion, "一桩桩都还清楚")
    body = "；".join(m.rstrip("。.") for m in mems[:2])
    return f"说起{cue}，{lead}——{body}。这些啊，我都没忘。"

"""声气：让分身开口时带着活人的语气——说笑话先"嘿嘺"一声、报忧前轻轻"唉"一下、
说到暖处先"嗯……"一顿。不是干巴巴的机器朗读，而是有呼吸、有情绪的那口气。

只在一句话前缀一个**能读出来的**小语气词（不是括号舞台提示，免得 TTS 把"括号"也念出来），
轻、准、不啰嗦。纯逻辑、可单测。给 perform 的有声版按情绪/话意挑一口气。
"""

from __future__ import annotations

# 能被语音合成读出来的起头小词（按情绪/话意挑一个）
_FUNNY = ("笑话", "逗", "段子", "搞笑", "哈哈", "好玩", "乐呵")
_SAD = ("难过", "走了", "不在了", "去世", "想他", "想她", "舍不得", "哭", "伤心", "难受")
_TENDER = ("想你", "心疼", "疼你", "在乎", "乖", "我陪", "抱抱", "辛苦了", "爱你")
_FEAR = ("别怕", "没事的", "有我", "我在", "稳住", "镇定", "扛得住")
_GREET = ("回来啦", "你来啦", "好久不见", "可算见着")


def _has(text, words) -> bool:
    t = str(text or "")
    return any(w in t for w in words)


def lead_cue(text, emotion=None, speakable=True) -> str:
    """这句话该先带的一口气：返回能读出来的小词；拿不准就空。

    speakable=False 时返回供"显示/仿真"的舞台提示（带括号），不会送进 TTS。
    """
    t = str(text or "")
    em = emotion or ""
    # 笑——逗趣/讲段子
    if _has(t, _FUNNY) or em in ("乐",):
        return "嘿嘿，" if speakable else "（笑）"
    # 哽——报忧/思念逝者
    if _has(t, _SAD) or em == "哀":
        return "唉……" if speakable else "（轻轻叹了口气）"
    # 暖——心疼/陪伴
    if _has(t, _TENDER) or em == "爱":
        return "嗯……" if speakable else "（声音放软）"
    # 稳——安抚害怕
    if _has(t, _FEAR) or em == "惧":
        return "别急，" if speakable else "（放缓声音）"
    # 喜——见面招呼
    if _has(t, _GREET) or em == "喜":
        return "哎，" if speakable else "（眼睛一亮）"
    # 惊叹
    if t.rstrip().endswith(("！", "!")):
        return "哎呀，" if speakable else "（提了口气）"
    return ""


def voice_lead(text, emotion=None) -> str:
    """整句的有声起头：把该带的那口气缀在最前面（已是能读出来的词）。"""
    cue = lead_cue(text, emotion, speakable=True)
    if not cue:
        return str(text or "")
    head = str(text or "").lstrip()
    # 起头已经是语气词了就不重复（如本来就"哎呀…"开头）
    if head[:1] in "嘿唉嗯哎别" and cue.rstrip("，…") and head.startswith(cue.rstrip("，…")):
        return str(text or "")
    return cue + head


def stage_note(text, emotion=None) -> str:
    """给文字/仿真看的舞台提示（带括号，不会送进语音），拿不准返回空。"""
    return lead_cue(text, emotion, speakable=False)

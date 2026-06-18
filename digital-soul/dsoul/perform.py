"""说与动合一：分身开口时，身体跟着话走——重点处点头、句间问话侧首、说到暖处倾身。
让"说话"和"动作"是一个浑然的人，而不是两套各管各的系统。

把一段话按句切成"节拍"，每拍配一个随话意/情绪的小动作。纯逻辑、可单测；
真机器人按节拍"说一句 + 动一下"交替来，仿真则把整段编排打印出来。
"""

from __future__ import annotations

import re

_SENT = re.compile(r"[^。！？!?\n]+[。！？!?]?")


def _gesture_for(sentence, emotion):
    s = (sentence or "").rstrip()
    if s.endswith(("？", "?")):
        return ("微微侧首", "带着问意看你")
    if any(k in s for k in ("想你", "心疼", "疼你", "在乎", "舍不得", "爱你", "我陪", "暖")):
        return ("温柔倾身", "声音放软，朝你侧过身")
    if any(k in s for k in ("记得", "别忘", "一定", "千万", "听我的", "按时", "当心")):
        return ("点头叮嘱", "认真地点点头")
    if s.endswith(("！", "!")):
        return ("用力点头", "带着劲儿")
    from .embodiment import body_language
    return body_language(emotion)


def beats(text, emotion=None) -> list:
    """把一段话切成 [(说的一句, (体态, 细节)), ...] 的节拍。"""
    out = []
    for m in _SENT.finditer(str(text or "")):
        seg = m.group().strip()
        if seg:
            out.append((seg, _gesture_for(seg, emotion)))
    return out


def perform(robot, text, emotion=None) -> None:
    """按节拍演出：说一句、配一个动作，交替着来，像真人边说边动。"""
    if robot is None:
        return
    bs = beats(text, emotion)
    if not bs:
        try:
            robot.say(str(text or ""))
        except Exception:
            pass
        return
    for seg, (gname, gdetail) in bs:
        try:
            robot.say(seg)
        except Exception:
            pass
        fn = getattr(robot, "gesture", None)
        if callable(fn):
            try:
                fn(gname, gdetail)
            except Exception:
                pass

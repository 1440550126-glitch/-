"""哄你开心：察觉你情绪低，分身不只安慰，还主动想法子把你暖回来——
说件开心的旧事、讲个段子、放首你爱的歌、撺掇你给想念的人打个电话。

把已有的几样（段子/老歌/小确幸/牵挂）凑成一招"主动哄"。纯逻辑、可单测。
"""

from __future__ import annotations

_LEAD = ["来，别耷拉着脸，我有办法逗你乐。", "哎，看你不痛快，我来哄哄你。",
         "走，咱不愁了，我陪你换个心情。"]


def lift(joke="", song="", joy="", call_who="", seed="") -> str:
    """凑一招哄人开心：开个头，再挑一两样能暖到的事。"""
    s = str(seed)
    parts = [_LEAD[len(s) % len(_LEAD)]]
    picks = []
    if joke:
        picks.append(f"先给你讲个乐子——{joke}")
    if joy:
        picks.append(f"再说件开心的：{str(joy).rstrip('。.')}，想起来就该笑。")
    if song:
        picks.append(f"要不放一首{song}，咱跟着哼两句。")
    if call_who:
        picks.append(f"要不给{call_who}打个电话？听听TA的声音，心里就敞亮了。")
    if not picks:
        picks.append("陪我说说话，啥都行，闷着最难受。")
    parts.extend(picks[:2])     # 别一股脑全上，挑一两样
    parts.append("有我在呢，天大的不痛快也会过去的。")
    return " ".join(parts)


def is_lift_request(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("哄哄我", "哄我开心", "逗我开心", "心情不好", "心情不太好",
                                "不开心", "高兴不起来", "让我开心", "哄我"))

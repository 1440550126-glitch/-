"""陪伴与守护：像一个就在身边、活生生的人那样，按时候问一句、提醒一句、暖一句。

不谈生死，只说眼下——你吃了吗、天凉加衣、累了就歇、我在呢。让分身有"人味儿"、更主动。
分身用它做主动陪伴（见面问候、按时段关心、健康守护、有人难过时接住）。纯逻辑、可单测。
"""

from __future__ import annotations

from datetime import datetime


def time_of_day(now=None) -> str:
    """把一天分成几个时段。"""
    h = (now or datetime.now()).hour
    if 5 <= h < 9:
        return "清晨"
    if 9 <= h < 11:
        return "上午"
    if 11 <= h < 13:
        return "中午"
    if 13 <= h < 17:
        return "下午"
    if 17 <= h < 19:
        return "傍晚"
    if 19 <= h < 23:
        return "晚上"
    return "深夜"


_GREETING = {
    "清晨": ["早呀，昨晚睡得好吗？", "早上好，今天也要好好的。"],
    "上午": ["上午忙着呢？别太赶，悠着点。", "上午好，记得喝口水。"],
    "中午": ["晌午了，记得吃口热乎饭。", "中午歇一会儿，眯一下更精神。"],
    "下午": ["下午容易乏，起来走两步、喝口水。", "下午好，别老盯着屏幕，看看远处。"],
    "傍晚": ["这就到点了，今天累不累？", "傍晚了，慢些走，注意脚下。"],
    "晚上": ["晚上好，今天过得咋样？", "忙了一天，泡泡脚、早点歇。"],
    "深夜": ["这么晚还没睡？早点休息，别熬着。", "夜深了，关了灯歇着吧，我陪着你。"],
}

# 暖心在场感（让人觉得"TA 就在身边"）
_PRESENCE = ["我在呢。", "有我陪着你。", "别怕，我一直都在。", "想说啥就跟我说，我听着。"]

# 有人流露疲惫/难过/孤单（任何家人，非专指老伴）
_DOWN = ("累了", "好累", "撑不住", "扛不住", "难过", "不开心", "压力大", "好烦", "心烦",
         "孤单", "委屈", "想哭", "没劲", "提不起劲", "好难")


def greeting_for(now=None, seed="") -> str:
    """按时段挑一句问候（按 seed 取，可复现）。"""
    opts = _GREETING.get(time_of_day(now), ["我在呢。"])
    return opts[len(str(seed)) % len(opts)]


def presence_line(seed="") -> str:
    """一句在场感。"""
    return _PRESENCE[len(str(seed)) % len(_PRESENCE)]


def weather_care(weather) -> str:
    """看天气/气温送一句关心。weather 可以是文字（'下雨'）或带'冷/热'的提示。"""
    if not weather:
        return ""
    w = str(weather)
    if any(k in w for k in ("冷", "凉", "雪", "降温", "寒")):
        return "天有点凉，加件衣裳，别冻着。"
    if "雨" in w:
        return "外头下雨，出门带把伞。"
    if any(k in w for k in ("热", "高温", "晒")):
        return "天热，多喝水、别中暑。"
    if any(k in w for k in ("风", "雾", "霾")):
        return "外头风大，出门当心，戴个口罩。"
    return ""


def checkin(now=None, weather=None, seed="") -> str:
    """一句贴心的陪伴：时段问候 +（看天气）一句关心。"""
    parts = [greeting_for(now, seed)]
    wc = weather_care(weather)
    if wc:
        parts.append(wc)
    return " ".join(parts)


def wellbeing_nudge(now=None) -> str:
    """按时段的健康守护：到点提醒吃饭/活动/睡觉（不在这些点则空）。"""
    return {
        "中午": "到饭点了，记得吃午饭，别凑合。",
        "傍晚": "该准备晚饭了，按时吃，别饿着。",
        "晚上": "吃过晚饭了吗？吃了就歇会儿。",
        "下午": "坐久了起来活动活动，喝口水。",
        "深夜": "真的不早了，早点睡，熬夜伤身子。",
    }.get(time_of_day(now), "")


def senses_down(utterance) -> bool:
    """有人在流露疲惫/难过/孤单。"""
    u = utterance or ""
    return any(k in u for k in _DOWN)


def comfort(utterance="", name="", seed="") -> str:
    """有人累了/难过了，以"我就在身边"的暖意接住（present-tense，不提生死）。"""
    who = (str(name) + "，") if name else ""
    u = utterance or ""
    if "累" in u or "撑不住" in u or "扛不住" in u:
        extra = "累了就歇会儿，身体要紧，活儿是干不完的。"
    elif any(k in u for k in ("难过", "想哭", "委屈")):
        extra = "想哭就哭出来，我陪着你，不急。"
    elif any(k in u for k in ("孤单", "一个人")):
        extra = "别觉得孤单，我一直在你身边呢。"
    else:
        extra = "歇一歇，天大的事也有我陪你一块儿扛。"
    return f"{who}{presence_line(seed)} {extra}"

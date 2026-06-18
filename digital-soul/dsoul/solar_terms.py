"""二十四节气：到了节气，像家里老人那样念一句时令与养生的叮嘱。

公历日期每年差一两天，这里用通用日期判断"当前处在哪个节气"。纯数据 + 纯逻辑、可单测。
Agent.solar_term_today() / seasonal_wisdom() 调用本模块；分身会在见到你时顺口提一句。
"""

from __future__ import annotations

from datetime import date, datetime

# (节气名, 通用公历 MM-DD, 一句时令/养生叮嘱)。按一年时序排列。
_TERMS = [
    ("小寒", "01-06", "一年最冷的开头，护好膝盖和脚，喝点热的。"),
    ("大寒", "01-20", "最冷的时候，别逞强，少出门、多添衣。"),
    ("立春", "02-04", "春天来了，添点绿叶菜，早睡早起别熬夜。"),
    ("雨水", "02-19", "雨水多、地返潮，出门当心滑，关节别受凉。"),
    ("惊蛰", "03-06", "万物醒了，多走动走动，别赖着不动。"),
    ("春分", "03-21", "昼夜一样长，吃睡都讲个均匀，别太累。"),
    ("清明", "04-05", "清明了，去看看想念的人，也出门踏踏青。"),
    ("谷雨", "04-20", "雨生百谷，湿气重，喝点祛湿的，别贪凉。"),
    ("立夏", "05-06", "入夏了，午后歇个晌，心要静、火要降。"),
    ("小满", "05-21", "麦子将满未满，吃清淡点，别上火。"),
    ("芒种", "06-06", "农忙时节，出汗多，水要喝够，别中暑。"),
    ("夏至", "06-21", "白天最长，晚点睡早点起，别贪冷饮。"),
    ("小暑", "07-07", "热起来了，避开正午的日头，绿豆汤备着。"),
    ("大暑", "07-23", "一年最热，别贪空调，西瓜适量，护好肠胃。"),
    ("立秋", "08-08", "秋天起头，早晚转凉，别再光膀子了。"),
    ("处暑", "08-23", "暑气要退，添件薄衣，润润肺、多喝水。"),
    ("白露", "09-08", "露水重了，夜里盖好被子，别冻着肚子。"),
    ("秋分", "09-23", "昼夜又均分，吃点润的，秋燥伤肺。"),
    ("寒露", "10-08", "天真凉了，脚要保暖，别再穿凉鞋。"),
    ("霜降", "10-23", "要下霜了，进补从这会儿起，护好脾胃。"),
    ("立冬", "11-08", "冬天来了，早睡晚起，吃点热乎的补补。"),
    ("小雪", "11-22", "天要落雪，多晒太阳，心里也要暖。"),
    ("大雪", "12-07", "雪大天寒，进补正当时，别忘了动一动。"),
    ("冬至", "12-22", "冬至大如年，吃顿饺子，一家人聚聚。"),
]


def _md(now=None) -> tuple:
    now = now or datetime.now()
    return now.month, now.day


def _as_md(s):
    m, d = s.split("-")
    return int(m), int(d)


def current_term(now=None):
    """当前所处的节气（最近一个已到的节气）。返回 (名, MM-DD, 叮嘱)。"""
    m, d = _md(now)
    today = (m, d)
    # 找今年里"日期 <= 今天"的最后一个节气；都没到（一月初）则取上一年的大雪/冬至
    passed = [t for t in _TERMS if _as_md(t[1]) <= today]
    return passed[-1] if passed else _TERMS[-1]


def term_on(now=None, window=1):
    """今天是否正赶上某个节气（前后 window 天内）。是则返回该节气，否则 None。"""
    now = now or datetime.now()
    today = now.date()
    for name, md, tip in _TERMS:
        m, d = _as_md(md)
        try:
            day = date(today.year, m, d)
        except ValueError:
            continue
        if abs((today - day).days) <= window:
            return (name, md, tip)
    return None


def wisdom(term) -> str:
    """节气叮嘱：『（霜降）要下霜了……』"""
    if not term:
        return ""
    name, _md_, tip = term
    return f"（{name}）{tip}"


def seasonal_wisdom(now=None) -> str:
    """当前时令的一句叮嘱（不论是否正卡在节气当天）。"""
    return wisdom(current_term(now))


def next_term(now=None):
    """下一个节气与还有几天：(名, days_left)。"""
    now = now or datetime.now()
    today = now.date()
    best = None
    for name, md, _tip in _TERMS:
        m, d = _as_md(md)
        try:
            day = date(today.year, m, d)
        except ValueError:
            continue
        if day < today:
            try:
                day = date(today.year + 1, m, d)
            except ValueError:
                continue
        left = (day - today).days
        if best is None or left < best[1]:
            best = (name, left)
    return best

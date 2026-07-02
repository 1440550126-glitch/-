"""世界时间 / 时差：孩子在国外，惦记着"那边现在几点、睡了没"——这一块替你算。
给个城市/国家，按和北京（东八区）的时差，算出当地此刻几点、差几个小时，
顺便提醒"别在人家睡觉时打电话"。纯逻辑、可单测。

⚠️ 用的是标准时差；不少地方有夏令时（夏天拨快一小时），算出来可能差一小时，
拿不准就提醒对方报一下当地时间。
"""

from __future__ import annotations

from datetime import datetime, timedelta

_CHINA_OFFSET = 8.0
_WEEK = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 地名/别名 -> (规范名, UTC 偏移小时, 是否有夏令时)
_ZONES = {
    "纽约": ("纽约", -5, True), "华盛顿": ("华盛顿", -5, True), "波士顿": ("波士顿", -5, True),
    "芝加哥": ("芝加哥", -6, True),
    "洛杉矶": ("洛杉矶", -8, True), "旧金山": ("旧金山", -8, True), "西雅图": ("西雅图", -8, True),
    "美国": ("美国（东部为准）", -5, True), "美东": ("美国东部", -5, True), "美西": ("美国西部", -8, True),
    "多伦多": ("多伦多", -5, True), "温哥华": ("温哥华", -8, True), "加拿大": ("加拿大（东部为准）", -5, True),
    "伦敦": ("伦敦", 0, True), "英国": ("英国", 0, True),
    "巴黎": ("巴黎", 1, True), "法国": ("法国", 1, True), "柏林": ("柏林", 1, True),
    "德国": ("德国", 1, True), "罗马": ("罗马", 1, True), "意大利": ("意大利", 1, True),
    "马德里": ("马德里", 1, True), "西班牙": ("西班牙", 1, True),
    "莫斯科": ("莫斯科", 3, False), "俄罗斯": ("俄罗斯（莫斯科）", 3, False),
    "迪拜": ("迪拜", 4, False), "阿联酋": ("阿联酋", 4, False),
    "新德里": ("新德里", 5.5, False), "印度": ("印度", 5.5, False),
    "曼谷": ("曼谷", 7, False), "泰国": ("泰国", 7, False),
    "新加坡": ("新加坡", 8, False), "香港": ("香港", 8, False), "台北": ("台北", 8, False),
    "东京": ("东京", 9, False), "日本": ("日本", 9, False),
    "首尔": ("首尔", 9, False), "韩国": ("韩国", 9, False),
    "悉尼": ("悉尼", 10, True), "墨尔本": ("墨尔本", 10, True), "澳大利亚": ("澳大利亚（悉尼）", 10, True),
    "奥克兰": ("奥克兰", 12, True), "新西兰": ("新西兰", 12, True),
}


def _all(config=None) -> dict:
    d = dict(_ZONES)
    cfg = (config or {}).get("timezones") if isinstance(config, dict) else None
    if isinstance(cfg, dict):
        for name, v in cfg.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]) if len(v) > 2 and v[0] else str(name),
                                float(v[1]), bool(v[2]) if len(v) > 2 else False) \
                    if len(v) >= 3 else (str(name), float(v[1]), False)
    return d


def find_place(utterance, config=None):
    """认出话里的地名（最长匹配）。返回 (规范名, 偏移, 夏令时) 或 None。"""
    u = str(utterance or "")
    best, best_len = None, 0
    for name in sorted(_all(config), key=len, reverse=True):
        if name in u and len(name) > best_len:
            best, best_len = _all(config)[name], len(name)
    return best


def _fmt_hours(h: float) -> str:
    h = abs(h)
    if abs(h - int(h)) < 1e-9:
        return f"{int(h)} 个小时"
    return f"{int(h)} 个半小时"      # 仅出现 .5 的情形（如印度 +5:30）


def diff_text(offset: float) -> str:
    """和北京的时差描述。"""
    d = offset - _CHINA_OFFSET
    if abs(d) < 1e-9:
        return "和北京同一个时间"
    return f"比北京{'早' if d > 0 else '晚'}{_fmt_hours(d)}"


def time_in(place, now=None, config=None) -> str:
    """某地此刻几点（按标准时差）。认不出地名返回空。"""
    info = place if isinstance(place, tuple) else find_place(place, config)
    if not info:
        return ""
    name, offset, dst = info
    now = now or datetime.now()
    target = now + timedelta(hours=offset - _CHINA_OFFSET)
    wd = _WEEK[target.weekday()]
    body = f"{name}现在是 {target.month}月{target.day}日 {wd} {target.hour:02d}:{target.minute:02d}，{diff_text(offset)}"
    if dst:
        body += "（有夏令时，夏天可能再差一小时）"
    return body + "。"


def call_advice(place, now=None, config=None) -> str:
    """顺带提醒：那边是不是正睡着（22 点~7 点别打扰）。"""
    info = place if isinstance(place, tuple) else find_place(place, config)
    if not info:
        return ""
    now = now or datetime.now()
    target = now + timedelta(hours=info[1] - _CHINA_OFFSET)
    if target.hour >= 22 or target.hour < 7:
        return "那边这会儿多半睡了，要不等会儿再联系？"
    return "这个点联系正合适。"


def answer(utterance, now=None, config=None) -> str:
    """一句话回答某地此刻几点 + 是否方便联系。认不出返回空。"""
    info = find_place(utterance, config)
    if not info:
        return ""
    t = time_in(info, now=now, config=config)
    adv = call_advice(info, now=now, config=config)
    return f"{t}{adv}"


def is_timezone_query(utterance, config=None) -> bool:
    """是不是在问国外某地时间/时差（有外地地名 + 时间/时差意图）。"""
    u = str(utterance or "")
    if not find_place(u, config):
        return False
    return any(k in u for k in ("几点", "时间", "时差", "差几个", "差几", "睡了", "睡没",
                                "现在是几", "当地时间", "几点了"))


def count(config=None) -> int:
    return len(_all(config))

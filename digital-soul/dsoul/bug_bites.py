"""防蚊虫叮咬：蚊子咬了怎么止痒、被蜂蜇了怎么办、蜱虫叮上千万别硬拔——
夏天虫子多，有的咬一口没事、有的可大意不得。怎么防、咬了怎么处理，说清楚。纯逻辑、可单测。

⚠️ 蜂蜇后喉头发紧/呼吸困难（过敏），或被群蜂蜇、蜱虫叮咬后发烧皮疹——立刻就医/打 120。
"""

from __future__ import annotations

# 虫 -> (咬了怎么办, 警示/怎么防)
_BUGS = {
    "蚊子": ("咬的包又痒又肿：抹点炉甘石洗剂、清凉油或花露水止痒，别抓破（抓破易感染）;冷敷也能消肿。",
           "防蚊：挂蚊帐、用驱蚊液、清掉家里花盆托盘的积水（蚊子在水里生）。"),
    "蜂蜇": ("先看有没有留下毒刺，有就用卡片'刮'出来（别用手挤，越挤毒越多）;冷敷消肿、涂点药;一般几天好。",
           "⚠️ 要是蜇后起大片疹子、喉咙发紧、呼吸困难、头晕（全身过敏），或被群蜂蜇、蜇在口咽——立刻打 120！"),
    "蜱虫": ("蜱虫钻进皮肤别硬拔、别拍死、别用手捏爆——用尖镊子'贴着皮肤'夹住头部，稳稳地直直拔出来，"
           "再用碘伏消毒;实在弄不下来去医院取。",
           "⚠️ 拔出后几周内若发烧、乏力、起皮疹，赶紧就医并说明被蜱虫咬过（防传染病）。野外活动扎紧裤腿。"),
    "隐翅虫": ("停在身上的隐翅虫别拍死（体液有强酸会灼伤皮肤）——'吹走或抖掉';"
            "万一沾到，赶紧用大量清水冲洗、别揉、别抓，起水疱别弄破。",
            "起红肿水疱、范围大或在脸上，去皮肤科看看。"),
    "毛毛虫": ("沾了毛毛虫的毒毛刺痛痒：别用手揉，用'胶带'反复粘掉毒毛，再用清水冲洗、涂点止痒药。",
            "肿痛厉害或过敏就医。"),
    "防叮咬": ("出门尤其去草丛、树林：穿长袖长裤、扎紧裤腿、喷驱蚊液;家里挂蚊帐、纱窗关好、清积水;"
            "宠物也定期驱虫。",
            "蜱虫多在草丛树林，去这些地方更要遮挡好。"),
}

_ALIAS = {
    "蚊子": "蚊子", "蚊子咬": "蚊子", "蚊子包": "蚊子", "被蚊子": "蚊子", "蚊虫叮咬": "蚊子",
    "蜂蜇": "蜂蜇", "蜜蜂蜇": "蜂蜇", "马蜂蜇": "蜂蜇", "被蜂": "蜂蜇", "黄蜂": "蜂蜇", "蜂子蜇": "蜂蜇",
    "蜱虫": "蜱虫", "草爬子": "蜱虫", "壁虱": "蜱虫",
    "隐翅虫": "隐翅虫", "影子虫": "隐翅虫",
    "毛毛虫": "毛毛虫", "洋辣子": "毛毛虫", "刺毛虫": "毛毛虫",
    "防叮咬": "防叮咬", "防蚊虫": "防叮咬", "怎么防虫": "防叮咬",
}


def _all(config=None) -> dict:
    d = dict(_BUGS)
    cfg = (config or {}).get("bug_bites") if isinstance(config, dict) else None
    extra = (cfg or {}).get("bugs") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("how"):
                d[str(name)] = (str(v["how"]), str(v.get("warn", "")))
    return d


def bugs(config=None) -> list:
    return list(_all(config).keys())


def find_bug(utterance, config=None):
    """认出问的哪种虫（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def advice(bug, config=None) -> str:
    """某种虫咬了怎么办 + 警示。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(bug or ""), str(bug or ""))
    if key not in d:
        return ""
    how, warn = d[key]
    return f"{key}：{how}" + (f" {warn}" if warn else "")


def overview() -> str:
    """防虫咬要点。"""
    return ("夏天防虫咬：蚊子包抹花露水/炉甘石别抓破;蜂蜇刮出毒刺冷敷、全身过敏立刻 120;"
            "蜱虫别硬拔、镊子贴皮拔出后消毒、几周内发烧就医;隐翅虫别拍死、吹走冲水。"
            "出门草丛穿长袖扎裤腿、喷驱蚊液。")


def is_bite_query(utterance, config=None) -> bool:
    """是不是在问虫咬/防虫。"""
    u = str(utterance or "")
    if not find_bug(u, config):
        return False
    return any(k in u for k in ("咬", "蜇", "叮", "怎么办", "怎么", "咋办", "止痒", "防", "肿",
                                "怎么处理", "要紧吗", "有事吗", "能拍", "拍吗", "能不能", "吗"))


def count(config=None) -> int:
    return len(_all(config))

"""足部护理：人老脚先老，脚舒服了走得稳、走得远。泡脚、脚气、灰指甲、鸡眼、脚后跟干裂
怎么弄，尤其糖尿病人的脚要格外当心。纯逻辑、可单测。

⚠️ 糖尿病人足部小伤口都别大意（愈合慢、易感染），有问题及时看医生。
"""

from __future__ import annotations

# 主题 -> (怎么做, 提醒)
_TOPICS = {
    "泡脚": ("温水（40℃ 左右、不烫手）泡 15～20 分钟，睡前泡暖身助眠;泡后擦干、尤其脚趾缝。",
           "别太烫太久;糖尿病人或感觉迟钝的，水温要更低、时间短，先用手肘试温，免得烫伤不自知。"),
    "脚气": ("脚气是真菌感染（痒、脱皮、起泡）：保持脚干爽、鞋袜透气勤换勤晒、抹抗真菌药膏（坚持用够疗程）;"
           "别和家人共用拖鞋、脚盆、毛巾。",
           "反复不好、化脓了去皮肤科。"),
    "灰指甲": ("指甲变厚、变黄、变脆，多是真菌感染（甲癣），会传染。要看皮肤科、按医嘱用药，疗程比较长、得有耐心。",
            "别自己乱抠乱剪传染别处;和脚气一起治才断根。"),
    "鸡眼老茧": ("鸡眼、老茧是长期挤压摩擦磨出来的：换'合脚不挤'的鞋、温水泡软后慢慢磨薄、可贴鸡眼膏。",
             "别自己用刀片割（容易感染）;糖尿病人尤其别自行处理，交给医生。"),
    "脚后跟干裂": ("泡软后轻轻去掉厚角质，抹凡士林或护足霜、再穿上袜子'封'住，坚持几天就软了。",
               "裂口深、出血、疼，别硬撕，涂药护着;反复裂查查有没有脚气或别的问题。"),
    "糖尿病足": ("糖尿病人的脚要当成宝贝护：每天检查脚底脚趾有没有破口水泡、别赤脚走、别用太烫的水、"
             "穿宽松不磨脚的鞋袜、剪指甲平着剪别太短。",
             "⚠️ 再小的伤口、起泡、变色都别拖，及时看医生——糖尿病足拖不得。"),
    "剪脚指甲": ("平着剪、别剪太深太短、两角别剪进肉里（防嵌甲发炎）;太厚不好剪先泡软;"
             "自己看不清、够不着，让家人帮忙。",
             "嵌甲红肿化脓了别硬抠，去医院处理。"),
}

_ALIAS = {
    "泡脚": "泡脚", "热水泡脚": "泡脚", "泡脚水温": "泡脚",
    "脚气": "脚气", "足癣": "脚气", "脚痒脱皮": "脚气",
    "灰指甲": "灰指甲", "甲癣": "灰指甲", "指甲变厚": "灰指甲",
    "鸡眼老茧": "鸡眼老茧", "鸡眼": "鸡眼老茧", "老茧": "鸡眼老茧", "脚垫": "鸡眼老茧",
    "脚后跟干裂": "脚后跟干裂", "脚干裂": "脚后跟干裂", "脚跟裂": "脚后跟干裂", "脚裂口": "脚后跟干裂",
    "糖尿病足": "糖尿病足", "糖尿病人的脚": "糖尿病足", "糖尿病脚": "糖尿病足",
    "剪脚指甲": "剪脚指甲", "剪指甲": "剪脚指甲", "嵌甲": "剪脚指甲", "脚趾甲": "剪脚指甲",
}


def _all(config=None) -> dict:
    d = dict(_TOPICS)
    cfg = (config or {}).get("foot_care") if isinstance(config, dict) else None
    extra = (cfg or {}).get("topics") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("how"):
                d[str(name)] = (str(v["how"]), str(v.get("tip", "")))
    return d


def topics(config=None) -> list:
    return list(_all(config).keys())


def find_topic(utterance, config=None):
    """认出问的哪类足部护理（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def advice(topic, config=None) -> str:
    """某类足部护理怎么做 + 提醒。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(topic or ""), str(topic or ""))
    if key not in d:
        return ""
    how, tip = d[key]
    return f"{key}：{how}" + (f"（{tip}）" if tip else "")


def overview() -> str:
    """足部护理要点。"""
    return ("护脚记几条：温水泡脚别太烫、泡后擦干脚趾缝;脚气保持干爽抹药、别共用拖鞋;"
            "鸡眼老茧换合脚鞋、别自己割;脚跟干裂泡软抹凡士林;剪指甲平着剪别太深。"
            "糖尿病人的脚最要当心，小伤口也得看医生。")


def is_foot_query(utterance, config=None) -> bool:
    """是不是在问足部护理。"""
    u = str(utterance or "")
    if not find_topic(u, config):
        return False
    return any(k in u for k in ("怎么", "咋", "怎么办", "护理", "是什么", "要紧吗", "咋办",
                                "多少度", "能不能", "该", "好不好", "怎么弄", "注意", "注意啥"))


def count(config=None) -> int:
    return len(_all(config))

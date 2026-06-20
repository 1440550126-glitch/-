"""护眼护耳：上了年纪眼睛耳朵最先老。怎么日常养护、哪些信号要赶紧看医生、
老花助听器怎么配——说清楚，别将就也别耽误。纯逻辑、可单测。
和"导诊"(triage 挂哪科)、"膳食"(nutrition 护眼吃啥)接着用，这里讲日常护理和警示。

⚠️ 突发的眼痛+看不清、视野缺损、眼前黑幕，是急症（青光眼/视网膜脱离），别等，立刻去眼科急诊。
"""

from __future__ import annotations

# 主题 -> (日常怎么养, 警示/提醒)
_TOPICS = {
    "护眼日常": ("看书看手机别太久，用 20 分钟抬头看远处 20 秒歇歇；光线要足、别在黑暗里玩手机；"
              "手机字调大、调暖色;多眨眼别让眼睛干。",
              "看东西越来越花、雾，别硬扛，去眼科查查。"),
    "老花眼": ("到年纪看近处模糊是正常老化，配副合适的老花镜就清楚了，别将就着眯眼看伤眼。",
            "度数会变，隔两三年验一次光、换镜；老花同时看远也花，查查别的眼病。"),
    "白内障": ("看东西像隔层毛玻璃、雾蒙蒙、越来越花、怕光，可能是白内障——常见的老年眼病。",
            "去眼科确诊;成熟到影响生活可做手术（换人工晶体），是成熟的小手术，别太怕、也别拖太久。"),
    "青光眼": ("眼睛胀痛、看灯有彩虹圈、头痛恶心、视野像被遮了一块，可能是青光眼。",
            "⚠️ 急性发作会很快伤视力甚至失明——立刻去眼科急诊，别等！平时高眼压也要定期查。"),
    "飞蚊症": ("眼前有小黑点、小虫子似的飘来飘去，多数是玻璃体老化、良性的，别太焦虑。",
            "⚠️ 但要是黑点突然增多、伴随闪光感、或像有黑幕遮住一块，赶紧查眼底，防视网膜脱离。"),
    "干眼": ("眼睛干涩、酸胀、有异物感：少盯屏幕、多眨眼、热敷眼睛、屋里别太干，可点人工泪液。",
           "用眼后歇一歇；严重老不好去眼科看看。"),
    "护耳日常": ("别长时间大音量戴耳机（音量别超六成、连听别超一小时）；远离持续噪音；耳朵进水侧头控出来。",
              "听人说话总让人重复、看电视声音越开越大，可能听力在降，早点查。"),
    "掏耳朵": ("耳屎大多能自己慢慢排出，别用棉签、挖耳勺往深里捅——容易把耳屎推深、捅伤耳道甚至鼓膜。",
            "耳屎多了、堵得慌、影响听力，去医院让医生取，安全。"),
    "听力下降": ("老年性耳聋很常见，别不好意思：先去查听力，该配助听器就配，听得清才不闷、不糊涂、不孤单。",
              "突然一只耳朵听不见（突发性耳聋）要尽快就医，越早治越好。"),
    "助听器": ("助听器要到专业机构验配，按你的听力调，别图便宜网上随便买个不合适的；戴上有个适应期，慢慢习惯。",
            "定期复查、清洁保养；戴了听得清，生活质量大不一样。"),
}

_ALIAS = {
    "护眼日常": "护眼日常", "护眼": "护眼日常", "用眼": "护眼日常", "眼睛累": "护眼日常", "保护眼睛": "护眼日常",
    "老花眼": "老花眼", "老花": "老花眼", "老花镜": "老花眼",
    "白内障": "白内障", "眼睛雾": "白内障", "看东西模糊": "白内障",
    "青光眼": "青光眼", "眼胀痛": "青光眼", "看灯有彩虹": "青光眼",
    "飞蚊症": "飞蚊症", "飞蚊": "飞蚊症", "眼前黑点": "飞蚊症",
    "干眼": "干眼", "眼睛干": "干眼", "眼干涩": "干眼",
    "护耳日常": "护耳日常", "护耳": "护耳日常", "保护耳朵": "护耳日常", "耳机": "护耳日常",
    "掏耳朵": "掏耳朵", "挖耳朵": "掏耳朵", "耳屎": "掏耳朵", "耵聍": "掏耳朵",
    "听力下降": "听力下降", "耳背": "听力下降", "听不清": "听力下降", "耳聋": "听力下降", "听力": "听力下降",
    "助听器": "助听器", "配助听器": "助听器",
}


def _all(config=None) -> dict:
    d = dict(_TOPICS)
    cfg = (config or {}).get("vision_hearing") if isinstance(config, dict) else None
    extra = (cfg or {}).get("topics") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("care"):
                d[str(name)] = (str(v["care"]), str(v.get("warn", "")))
    return d


def topics(config=None) -> list:
    return list(_all(config).keys())


def find_topic(utterance, config=None):
    """认出问的哪类护眼护耳（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def advice(topic, config=None) -> str:
    """某类的养护 + 警示。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(topic or ""), str(topic or ""))
    if key not in d:
        return ""
    care, warn = d[key]
    return f"{key}：{care}" + (f" {warn}" if warn else "")


def is_vh_query(utterance, config=None) -> bool:
    """是不是在问护眼护耳。"""
    u = str(utterance or "")
    if not find_topic(u, config):
        return False
    return any(k in u for k in ("怎么", "咋", "是什么", "啥意思", "怎么办", "怎么养", "要紧吗",
                                "信号", "症状", "怎么回事", "该", "好不好", "能治吗", "怎么配"))


def count(config=None) -> int:
    return len(_all(config))

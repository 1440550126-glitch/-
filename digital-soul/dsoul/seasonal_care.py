"""换季防护：夏防中暑、冬防一氧化碳中毒和摔倒、春防过敏倒春寒、秋防干燥——
老人对天气最敏感，换季最容易出事。一条条说清楚怎么防，尤其冬天那条能救命。
纯逻辑、可单测。和"今天穿啥"(weather_day)、"节气养生"(tcm_wellness)接着用。
"""

from __future__ import annotations

# 防护主题 -> (要点, 危险信号/重点提醒)
_TOPICS = {
    "防中暑": ("避开正午（11–15 点）高温别出门、别在闷热密闭处久待；多喝水、出汗多加点淡盐水；"
            "备点藿香正气；戴帽打伞。",
            "中暑信号：头晕、恶心、没力气、皮肤发烫却不出汗——赶紧到阴凉处、解开衣领、降温补水，"
            "意识不清/高热不退立刻打 120。"),
    "防一氧化碳中毒": ("冬天最要命的一条：烧炭、煤炉、燃气热水器/灶一定要通风，别为了暖关死门窗；"
                  "屋里装个一氧化碳报警器最稳;洗澡别太久、热水器最好装在通风处或室外。",
                  "⚠️ 头晕、乏力、恶心、脸通红、迷糊，可能是一氧化碳中毒！立刻开门窗、关掉气源、"
                  "把人挪到通风处，赶紧打 120——别耽搁，这个要命。"),
    "防寒保暖": ("护好头、脖子、脚这几个怕冷的地方，戴帽围巾穿厚袜；早晚最冷少出门；"
              "室内别太干，可放盆水或加湿；起夜披件衣服别着凉。",
              "晨起别猛地坐起，缓一缓再下床，防头晕跌倒。"),
    "防心脑血管": ("天冷血管收缩、血压易高，是心梗脑梗的高发期：晨起慢点、出门保暖、按时吃药、"
                "别用劲（搬重物、使劲排便）、别情绪激动。",
                "突发胸闷胸痛、半身麻木说话不清，立刻打 120，抢时间。"),
    "防滑摔": ("雨雪结冰天能不出就不出；非出不可走慢点、穿防滑鞋、走有防滑垫的地方、扶好栏杆；"
            "屋里浴室铺防滑垫、装扶手。",
            "老人最怕摔，一摔可能卧床——慢就是稳。"),
    "防秋燥": ("秋天干，多喝水、吃点润的（梨、银耳、百合、蜂蜜水）；护好嘴唇和皮肤、抹点润肤；"
            "屋里干就加湿。",
            "嗓子干、皮肤痒、便秘多是燥，润一润就好。"),
    "防春困防过敏": ("春天'春捂'别急着减衣，乍暖还寒小心倒春寒；犯困多起来活动、开窗透气；"
                 "对花粉过敏的，花粉多的日子戴口罩、少去花草多的地方、回家洗脸洗手。",
                 "过敏起疹、流涕打喷嚏厉害，可备点抗过敏药，严重就医。"),
}

# 季节 -> 该季重点防护（按出现顺序）
_SEASON = {
    "夏": ["防中暑", "防滑摔"],
    "冬": ["防一氧化碳中毒", "防寒保暖", "防心脑血管", "防滑摔"],
    "春": ["防春困防过敏"],
    "秋": ["防秋燥"],
}

_ALIAS = {
    "防中暑": "防中暑", "中暑": "防中暑", "夏天注意": "防中暑", "夏季防护": "防中暑", "三伏": "防中暑",
    "防一氧化碳中毒": "防一氧化碳中毒", "一氧化碳": "防一氧化碳中毒", "煤气中毒": "防一氧化碳中毒",
    "烧炭": "防一氧化碳中毒", "燃气热水器": "防一氧化碳中毒", "煤炉": "防一氧化碳中毒",
    "防寒": "防寒保暖", "保暖": "防寒保暖", "防寒保暖": "防寒保暖", "冬天冷": "防寒保暖",
    "防心脑血管": "防心脑血管", "心梗": "防心脑血管", "脑梗": "防心脑血管", "天冷血压": "防心脑血管",
    "防滑": "防滑摔", "防摔": "防滑摔", "结冰路滑": "防滑摔", "下雪路滑": "防滑摔",
    "防秋燥": "防秋燥", "秋燥": "防秋燥", "秋天干": "防秋燥",
    "防春困": "防春困防过敏", "春困": "防春困防过敏", "倒春寒": "防春困防过敏",
    "花粉过敏": "防春困防过敏", "春捂": "防春困防过敏",
}


def _all(config=None) -> dict:
    d = dict(_TOPICS)
    cfg = (config or {}).get("seasonal_care") if isinstance(config, dict) else None
    extra = (cfg or {}).get("topics") if isinstance(cfg, dict) else None
    if isinstance(extra, dict):
        for name, v in extra.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                d[str(name)] = (str(v[0]), str(v[1]))
            elif isinstance(v, dict) and v.get("how"):
                d[str(name)] = (str(v["how"]), str(v.get("warn", "")))
    return d


def topics(config=None) -> list:
    return list(_all(config).keys())


def find_topic(utterance, config=None):
    """认出问的哪类防护（别名最长匹配）。听不出返回 None。"""
    u = str(utterance or "")
    for word in sorted(_ALIAS, key=len, reverse=True):
        if word in u:
            return _ALIAS[word]
    for name in _all(config):
        if name in u:
            return name
    return None


def advice(topic, config=None) -> str:
    """某类防护的要点 + 提醒。查不到返回空。"""
    d = _all(config)
    key = _ALIAS.get(str(topic or ""), str(topic or ""))
    if key not in d:
        return ""
    how, warn = d[key]
    return f"{key}：{how}" + (f" {warn}" if warn else "")


def season_of(month) -> str:
    """月份归季（北半球）。"""
    m = int(month)
    return {12: "冬", 1: "冬", 2: "冬", 3: "春", 4: "春", 5: "春",
            6: "夏", 7: "夏", 8: "夏", 9: "秋", 10: "秋", 11: "秋"}.get(m, "")


def season_advice(season, config=None) -> str:
    """整季的防护提点（列该季重点几条的标题）。"""
    keys = _SEASON.get(str(season or ""), [])
    keys = [k for k in keys if k in _all(config)]
    if not keys:
        return ""
    return f"{season}天重点防这几样：" + "、".join(keys) + "。想细说哪样跟我说。"


def is_seasonal_care_query(utterance, config=None) -> bool:
    """是不是在问换季/季节防护。"""
    u = str(utterance or "")
    if any(k in u for k in ("换季", "这季节注意", "夏天注意什么", "冬天注意什么", "季节防护")):
        return True
    if find_topic(u, config) and any(k in u for k in ("怎么防", "咋防", "注意", "怎么办", "要紧吗",
                                                      "怎么预防", "防护", "保暖", "是什么", "症状")):
        return True
    return False


def count(config=None) -> int:
    return len(_all(config))

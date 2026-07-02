"""节气养生 / 中医小贴士：按季节给点养生的老话——春养肝、夏养心、秋养肺、冬养肾，
配上该吃啥、该注意啥。像个懂点养生的老人。纯数据 + 纯逻辑、可单测。
"""

from __future__ import annotations

_SEASON = {
    "春": {"养": "肝",
           "tips": ["少酸多甘，养养肝气", "早睡早起，多到外头走走舒展", "春捂，别急着脱棉衣"],
           "food": ["韭菜", "菠菜", "春笋", "红枣"]},
    "夏": {"养": "心",
           "tips": ["静心戒躁，午间打个盹", "多喝水，别贪凉", "吃点苦味清清心火"],
           "food": ["绿豆", "苦瓜", "莲子", "西瓜"]},
    "秋": {"养": "肺",
           "tips": ["润燥养肺，多喝温水", "早睡早起，收敛神气", "贴秋膘也别过量"],
           "food": ["梨", "百合", "银耳", "莲藕"]},
    "冬": {"养": "肾",
           "tips": ["早睡晚起，避寒就温", "进补养肾，护好腰和脚", "别熬夜，养精蓄锐"],
           "food": ["羊肉", "黑芝麻", "核桃", "山药"]},
}


def season_of(month) -> str:
    try:
        m = int(month)
    except (TypeError, ValueError):
        return "春"
    return {3: "春", 4: "春", 5: "春", 6: "夏", 7: "夏", 8: "夏",
            9: "秋", 10: "秋", 11: "秋"}.get(m, "冬")


def wellness(season) -> str:
    """一句应季养生贴士。"""
    s = _SEASON.get(season)
    if not s:
        return ""
    tips = "；".join(s["tips"])
    food = "、".join(s["food"])
    return f"（{season}养{s['养']}）{tips}。多吃点{food}。"


def food_for(season) -> list:
    return list(_SEASON.get(season, {}).get("food", []))


def is_wellness_query(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("养生", "这季节注意", "怎么养", "养生贴士", "这时候吃什么补",
                                "节气养生", "该补补", "养身子"))

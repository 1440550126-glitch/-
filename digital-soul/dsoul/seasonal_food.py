"""应季时鲜：现在吃什么水果蔬菜最当季——顺时令、图新鲜，也实惠。
像家里那个会过日子、懂吃的人，到点就念叨"这阵子的XX正好"。

纯数据 + 纯逻辑、可单测（传入 now 可复现）。按通行物候，南北略有差别。
"""

from __future__ import annotations

from datetime import datetime

# 季 → (当季水果, 当季蔬菜)
_SEASON = {
    "春": (["草莓", "樱桃", "枇杷", "菠萝", "青梅"],
           ["春笋", "香椿", "荠菜", "菠菜", "豌豆", "蒜苗"]),
    "夏": (["西瓜", "水蜜桃", "荔枝", "葡萄", "芒果", "杨梅", "哈密瓜"],
           ["黄瓜", "茄子", "苦瓜", "丝瓜", "西红柿", "毛豆", "空心菜"]),
    "秋": (["苹果", "梨", "柿子", "石榴", "橘子", "板栗", "猕猴桃"],
           ["莲藕", "南瓜", "白萝卜", "菱角", "山药", "芋头"]),
    "冬": (["橙子", "柚子", "甘蔗", "冬枣", "丑橘", "砂糖橘"],
           ["大白菜", "白萝卜", "冬笋", "菠菜", "红薯", "茼蒿"]),
}

_M2S = {3: "春", 4: "春", 5: "春", 6: "夏", 7: "夏", 8: "夏",
        9: "秋", 10: "秋", 11: "秋", 12: "冬", 1: "冬", 2: "冬"}


def season_of(month) -> str:
    return _M2S.get(int(month), "")


def in_season(month) -> dict:
    """这个月当季的水果、蔬菜。"""
    s = season_of(month)
    fruits, veggies = _SEASON.get(s, ([], []))
    return {"季节": s, "水果": list(fruits), "蔬菜": list(veggies)}


def whats_fresh(now=None) -> str:
    """一句话报当季时鲜。"""
    now = now or datetime.now()
    m = now.month
    d = in_season(m)
    if not d["季节"]:
        return ""
    fruits = "、".join(d["水果"][:4])
    veggies = "、".join(d["蔬菜"][:4])
    return (f"这阵子是{d['季节']}天，时令水果有{fruits}，"
            f"蔬菜数{veggies}最新鲜——顺着季节吃，又鲜又实惠。")


def is_in_season(item, month) -> bool:
    """某样果蔬这个月当不当季。"""
    d = in_season(month)
    name = str(item or "")
    return any(x in name or name in x for x in d["水果"] + d["蔬菜"])


def is_seasonal_query(utterance) -> bool:
    u = str(utterance or "")
    return any(k in u for k in ("当季", "应季", "时令", "时鲜", "这季节吃", "现在吃什么水果",
                                "什么水果当季", "什么菜新鲜", "当下吃什么", "什么应季",
                                "这时候吃啥", "什么时候的菜"))

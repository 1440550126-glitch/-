"""今天吃什么：到饭点犯愁，从家传菜里挑一道，应着时令、避开忌口，给个暖心建议。
菜谱/忌口/时令由 Agent 传入，这里管怎么挑、怎么说。纯逻辑、可单测。
"""

from __future__ import annotations

_SEASON_FOODS = {
    "春": ["香椿炒蛋", "春笋", "荠菜饺子", "韭菜盒子"],
    "夏": ["绿豆汤", "凉面", "拍黄瓜", "苦瓜炒蛋"],
    "秋": ["莲藕排骨汤", "南瓜粥", "炖梨", "板栗烧鸡"],
    "冬": ["萝卜炖羊肉", "白菜炖豆腐", "酸菜锅", "红烧肉"],
}


def season_of(month) -> str:
    try:
        m = int(month)
    except (TypeError, ValueError):
        return "春"
    if m in (3, 4, 5):
        return "春"
    if m in (6, 7, 8):
        return "夏"
    if m in (9, 10, 11):
        return "秋"
    return "冬"


def _ok(dish, avoid) -> bool:
    return not any(a and a in dish for a in (avoid or []))


def suggest(recipes=None, season=None, avoid=None, seed=""):
    """挑一道菜：先从家传菜里挑（避开忌口），没有就按时令推荐。"""
    s = str(seed)
    fam = [r for r in (recipes or []) if r and _ok(r, avoid)]
    if fam:
        return fam[len(s) % len(fam)], "family"
    pool = [d for d in _SEASON_FOODS.get(season or "春", []) if _ok(d, avoid)]
    if pool:
        return pool[len(s) % len(pool)], "season"
    return None, None


def what_to_eat(recipes=None, season=None, avoid=None, seed="") -> str:
    """一句暖心的"今天吃这个"建议。"""
    dish, kind = suggest(recipes, season, avoid, seed)
    if not dish:
        return "想吃啥跟我说，我陪你张罗。"
    if kind == "family":
        return f"今天做个{dish}吧？咱家的老味道，你最爱这口。"
    return f"今天做个{dish}吧，应季又养人。"

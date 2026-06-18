"""喜好：分身有自己的口味与脾性——爱吃什么、偏爱哪个季节、讨厌什么。
问"你爱吃啥"答得稳（每次一致），聊到某样东西也能表个态，像个有血有肉的人。

配在 config/preferences.yaml，或并入 identity.preferences。纯逻辑、可单测。
"""

from __future__ import annotations

_LIKE_Q = ("爱吃", "喜欢吃", "喜欢", "最爱", "爱喝", "口味", "偏爱", "爱玩", "中意", "爱看")
_DISLIKE_Q = ("讨厌", "不爱吃", "不喜欢", "最烦", "不爱", "忌口", "最怕")

# 类别 → 关键词
_CATS = {
    "食物": ("吃", "菜", "食物", "口味"),
    "饮品": ("喝", "茶", "酒", "饮", "咖啡"),
    "季节": ("季节", "天气"),
    "消遣": ("玩", "消遣", "爱好", "兴趣", "干什么", "打发"),
    "音乐": ("歌", "音乐", "曲", "戏"),
    "球队": ("球队", "球", "队"),
}


def _norm_map(d) -> dict:
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, (list, tuple)):
                vals = [str(x).strip() for x in v if str(x).strip()]
            elif v:
                vals = [str(v).strip()]
            else:
                vals = []
            if vals:
                out[str(k).strip()] = vals
    return out


def _merge(a, b) -> dict:
    out = {k: list(v) for k, v in a.items()}
    for k, v in b.items():
        out.setdefault(k, [])
        for x in v:
            if x not in out[k]:
                out[k].append(x)
    return out


def collect_preferences(config=None, identity=None) -> dict:
    """汇总喜好：config/preferences.yaml + identity.preferences。"""
    cfg = dict(config or {})
    idp = ((identity or {}).get("preferences") or {}) if isinstance(identity, dict) else {}
    likes = _merge(_norm_map(cfg.get("likes")), _norm_map(idp.get("likes")))
    dislikes = _merge(_norm_map(cfg.get("dislikes")), _norm_map(idp.get("dislikes")))
    return {"likes": likes, "dislikes": dislikes}


def likes_of(prefs, category) -> list:
    return list((prefs or {}).get("likes", {}).get(category, []))


def dislikes_of(prefs, category) -> list:
    return list((prefs or {}).get("dislikes", {}).get(category, []))


def _detect_category(utterance):
    u = utterance or ""
    for cat, kws in _CATS.items():
        if any(k in u for k in kws):
            return cat
    return None


def has_any(prefs) -> bool:
    p = prefs or {}
    return bool(p.get("likes") or p.get("dislikes"))


def answer_preference(prefs, utterance) -> str:
    """回答"你爱吃什么 / 你讨厌什么"。"""
    u = utterance or ""
    is_dislike = any(k in u for k in _DISLIKE_Q)
    is_like = any(k in u for k in _LIKE_Q)
    if not (is_like or is_dislike):
        return ""
    cat = _detect_category(u)
    likes, dislikes = (prefs or {}).get("likes", {}), (prefs or {}).get("dislikes", {})
    if is_dislike:
        items = dislikes.get(cat) if cat else None
        if not items:
            items = [x for vs in dislikes.values() for x in vs]
        return (f"我最不爱{('、'.join(items[:3]))}，一口都不想碰。") if items else ""
    items = likes.get(cat) if cat else None
    if not items:
        items = [x for vs in likes.values() for x in vs]
    if not items:
        return ""
    joined = "、".join(items[:3])
    if cat in ("食物", "饮品"):
        return f"我就好这口——{joined}，百吃不厌。"
    if cat:
        return f"说到{cat}，我偏爱{joined}。"
    return f"我喜欢的可多了——{joined}，样样都中意。"


def opinion_on(prefs, thing) -> str:
    """聊到某样东西，表个态（爱/不爱）。"""
    if not thing:
        return ""
    t = str(thing)
    for vs in (prefs or {}).get("likes", {}).values():
        for x in vs:
            if x and (x in t or t in x):
                return f"{x}啊，我可喜欢了。"
    for vs in (prefs or {}).get("dislikes", {}).values():
        for x in vs:
            if x and (x in t or t in x):
                return f"说起{x}，我可不太爱那个。"
    return ""

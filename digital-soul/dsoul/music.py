"""老歌：分身爱哼几句年轻时的歌，也能按心情给你点一首。让屋里有点声响、有点怀旧的暖。
配在 config/music.yaml（favorites / by_mood），或并入 identity。纯逻辑、可单测。
"""

from __future__ import annotations

_DEFAULT_FAVS = ["《东方红》", "《我的祖国》", "《年轻的朋友来相会》", "《茉莉花》",
                 "《歌唱祖国》", "《在那桃花盛开的地方》"]

# 七情 → 应景的歌
_BY_MOOD = {
    "喜": ["《好日子》", "《今天是个好日子》", "《难忘今宵》"],
    "乐": ["《好日子》", "《甜蜜蜜》"],
    "哀": ["《送别》", "《一剪梅》", "《故乡的云》"],
    "爱": ["《月亮代表我的心》", "《甜蜜蜜》", "《我只在乎你》"],
    "惧": ["《敢问路在何方》", "《真心英雄》"],
    "怒": ["《好汉歌》"],
    "欲": ["《在希望的田野上》"],
}


def favorites(config=None) -> list:
    """爱唱的歌：config 优先，否则用一组老歌。"""
    favs = (config or {}).get("favorites") if isinstance(config, dict) else None
    favs = [str(x).strip() for x in (favs or []) if str(x).strip()]
    return favs or list(_DEFAULT_FAVS)


def hum(config=None, seed="") -> str:
    """随口哼一句。"""
    favs = favorites(config)
    song = favs[len(str(seed)) % len(favs)]
    return f"（轻轻哼起了{song}）这调子，年轻时百听不厌。"


def song_for_mood(mood, config=None) -> str:
    """按心情点一首。"""
    by_mood = {}
    if isinstance(config, dict) and isinstance(config.get("by_mood"), dict):
        by_mood = config["by_mood"]
    pool = by_mood.get(mood) or _BY_MOOD.get(mood)
    if not pool:
        pool = favorites(config)
    song = pool[0]
    return f"这心情，来一首{song}正合适，我给你哼几句。"


def is_music_request(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("唱首歌", "点首歌", "哼一段", "哼一首", "放首歌", "来首歌",
                                "唱个歌", "想听歌", "唱一个"))

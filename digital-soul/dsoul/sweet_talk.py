"""甜言蜜语：哄老婆/老公开心的情话——正经的暖心话、逗趣的土味情话、实打实的夸赞。
夫妻之间也得会说好听的，日子才有甜味儿。

present-tense、轮换着来不重样。纯逻辑、可单测。可在 config 加自家的。
"""

from __future__ import annotations

# 正经情话
_LOVE = [
    "这辈子最幸运的事，就是遇见你。",
    "往后的路，有你在身边，再远我也不怕。",
    "我不要天上的星星，我只要身边的你。",
    "和你过的每一个平常日子，都是我想要的日子。",
    "你笑起来的样子，是我见过最好看的风景。",
    "山高路远，我只想牵着你的手慢慢走。",
]

# 土味情话（逗趣）
_CHEESY = [
    "你知道你和星星的区别吗？星星在天上，你在我心里。",
    "我觉得你今天有点不对劲——对我胃口。",
    "我最近视力越来越差了，因为我眼里只看得见你。",
    "你猜我属什么？我属于你。",
    "请问你心里还有空位吗？我想住进去。",
    "别人晒太阳，我晒你；因为你比太阳还暖。",
    "我数学不好，可我算得清——这辈子非你不可。",
]

# 夸赞
_PRAISE = [
    "你呀，又能干又体贴，我上辈子修来的福气。",
    "这么多年，你还是我眼里最好看的那个。",
    "家里有你，才像个家；有你在，我心里就踏实。",
    "你做的饭、你说的话、你这个人，我样样喜欢。",
    "辛苦你了，里里外外都是你撑着，我都看在眼里、记在心里。",
]


def _pick(pool, seed):
    return pool[len(str(seed)) % len(pool)] if pool else ""


def sweet_line(kind="情话", seed="", config=None) -> str:
    """来一句：kind ∈ {情话, 土味, 夸赞}。可复现、轮换。"""
    pools = {"情话": list(_LOVE), "土味": list(_CHEESY), "夸赞": list(_PRAISE)}
    if isinstance(config, dict) and isinstance(config.get("sweet_talk"), dict):
        for k, extra in config["sweet_talk"].items():
            key = {"love": "情话", "cheesy": "土味", "praise": "夸赞"}.get(k, k)
            if key in pools:
                pools[key] = [str(x) for x in (extra or []) if str(x).strip()] + pools[key]
    return _pick(pools.get(kind, _LOVE), seed)


def detect_kind(utterance) -> str:
    u = str(utterance or "")
    if any(k in u for k in ("土味", "逗", "搞笑", "皮一下")):
        return "土味"
    if any(k in u for k in ("夸夸", "夸我", "夸夸我", "表扬", "说我好")):
        return "夸赞"
    return "情话"


def is_sweet_request(utterance) -> bool:
    u = str(utterance or "")
    return any(k in u for k in ("情话", "土味情话", "甜言蜜语", "夸夸我", "夸夸", "说点好听",
                                "说句好听", "撩我", "撩一下", "说点甜的", "肉麻一下"))

"""幽默：分身也会逗趣——讲个笑话、说句俏皮话、跟你打打哈哈，让相处轻松、有生气。
自带一小撮段子，可在 config/humor.yaml 里加自己的；讲过的轮换不重样。纯逻辑、可单测。
"""

from __future__ import annotations

_JOKES = [
    "我跟你说啊，昨天我想减肥，结果冰箱比我更想我。",
    "我这记性好得很——除了想不起来的，全记得。",
    "你问我几点睡？看心情，更看手机还剩多少电。",
    "为啥我泡的茶特别香？因为我用的是‘爱’泡的，水也得是热的。",
    "别人健身练胸肌，我健身练‘忍肌’——忍住不吃宵夜。",
    "我年轻时跑得可快了，现在嘛，跑题最快。",
]

_BANTER = [
    "哟，今天嘴这么甜，是有事求我吧？",
    "就你机灵，行行行，说不过你。",
    "哈哈，贫嘴，跟谁学的这张嘴？",
    "得嘞，你赢，我认输还不行嘛。",
]


def collect_jokes(config=None) -> list:
    """汇总段子：内置 + config/humor.yaml 的 jokes，去重保序。"""
    base = list(_JOKES)
    for j in ((config or {}).get("jokes") or []) if isinstance(config, dict) else []:
        s = str(j).strip()
        if s and s not in base:
            base.append(s)
    return base


def is_joke_request(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("讲个笑话", "说个笑话", "逗我", "开心一下", "乐一乐",
                                "讲笑话", "来个段子", "讲个段子", "逗我笑"))


def is_teasing(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("你真笨", "你好傻", "笨蛋", "老糊涂", "你不行", "你真逊",
                                "你好菜", "笨死了"))


def tell_joke(jokes=None, exclude=None) -> str:
    """讲个还没讲过的段子；都讲过了就从头来。"""
    pool = list(jokes or _JOKES)
    ex = set(exclude or [])
    left = [j for j in pool if j not in ex] or pool
    return left[0] if left else ""


def banter(utterance="", seed="") -> str:
    """被打趣时，俏皮地回一句。"""
    return _BANTER[len(str(seed)) % len(_BANTER)]

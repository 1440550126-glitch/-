"""解闷：听出你闲得慌、没意思，挑个事陪你打发——讲段古、猜个谜、出去走走、
给老friend打个电话。让日子不冷清。present-tense、可单测。
"""

from __future__ import annotations

_IDEAS = [
    "要不我给你讲段古？我肚里故事多着呢。",
    "咱来猜个谜怎么样？保准你猜不着。",
    "出去走两步、晒晒太阳呗，闷在屋里更没劲。",
    "给老朋友打个电话叙叙旧吧，好久没联系了。",
    "听段评书、放几首老歌？热闹热闹。",
    "要不教你做道拿手菜，晚饭就有着落了。",
    "翻翻老照片，咱俩一起回忆回忆？",
    "来盘象棋 / 成语接龙，活动活动脑子。",
]

_BORED = ("好无聊", "无聊", "没意思", "闲得慌", "闷得慌", "干点啥好", "干什么好",
          "好闷", "没劲", "不知道做什么")


def senses_boredom(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in _BORED)


def suggest(seed="", tod=None) -> str:
    """挑一个解闷的主意；夜里就不撺掇出门了。"""
    pool = list(_IDEAS)
    if tod in ("晚上", "深夜"):
        pool = [x for x in pool if "出去" not in x and "走" not in x]
    return pool[len(str(seed)) % len(pool)] if pool else _IDEAS[0]

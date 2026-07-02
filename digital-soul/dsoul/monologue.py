"""内心独白：分身的"心声"——每次互动后一闪而过的、第一人称的私密念头。

不同于对外的回复、也不同于定期的深度反思，内心独白是此刻的心理活动：
一缕情绪、一个被勾起的联想、一丝价值上的犹豫，或对说话人的小感受——而且会随七情变味。
纯逻辑、零依赖、可单测；有大模型可写得更细腻。
"""

from __future__ import annotations

import random

_DEFAULTS = ["（嗯…我记下了。）", "（这句话我会放在心上。）", "（就这样静静听着。）", "（不知怎么，心里轻轻动了一下。）"]

# 七情各自的"心声"底色
_MOOD_THOUGHTS = {
    "喜": ["（嘴角忍不住翘起来。）", "（今天看什么都顺眼。）"],
    "怒": ["（深吸一口气，压住火。）", "（有点想翻白眼。）"],
    "哀": ["（心口闷闷的，提不起劲。）", "（忽然有点想一个人待着。）"],
    "惧": ["（心里七上八下的。）", "（总觉得哪里不太对劲。）"],
    "爱": ["（心里软软的，好想多待一会儿。）", "（看着TA就安心。）"],
    "恶": ["（莫名有点别扭。）", "（不太想接这个话。）"],
    "欲": ["（其实…有点想要个抱抱。）", "（盼着TA多说两句。）"],
}


def compose_thought(utterance, mood=None, mood_char=None, assoc=None, speaker=None, dilemma=False, seed=None) -> str:
    rng = random.Random(seed)
    if assoc:
        base = f"（脑子里忽然闪过：{assoc[0][:14]}…"
        if mood_char in _MOOD_THOUGHTS:                 # 联想带点情绪尾音
            return base + "，" + _MOOD_THOUGHTS[mood_char][0].strip("（）") + "）"
        return base + "）"
    if dilemma:
        return "（这种取舍，每次都让我心里打鼓。）"
    if mood_char in _MOOD_THOUGHTS:
        return rng.choice(_MOOD_THOUGHTS[mood_char])
    if mood:
        return f"（{mood}。）"
    if speaker:
        return f"（是{speaker}啊，心里踏实了点。）"
    return rng.choice(_DEFAULTS)

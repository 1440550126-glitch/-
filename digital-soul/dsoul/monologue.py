"""内心独白：分身的"心声"——每次互动后一闪而过的、第一人称的私密念头。

不同于对外的回复、也不同于定期的深度反思，内心独白是此刻的心理活动：
一缕情绪、一个被勾起的联想、一丝价值上的犹豫，或对说话人的小感受。
纯逻辑、零依赖、可单测；有大模型可写得更细腻。
"""

from __future__ import annotations

import random

_DEFAULTS = ["（嗯…我记下了。）", "（这句话我会放在心上。）", "（就这样静静听着。）", "（不知怎么，心里轻轻动了一下。）"]


def compose_thought(utterance, mood=None, assoc=None, speaker=None, dilemma=False, seed=None) -> str:
    if assoc:
        return f"（脑子里忽然闪过：{assoc[0][:14]}…）"
    if dilemma:
        return "（这种取舍，每次都让我心里打鼓。）"
    if mood:
        return f"（{mood}。）"
    if speaker:
        return f"（是{speaker}啊，心里踏实了点。）"
    return random.Random(seed).choice(_DEFAULTS)

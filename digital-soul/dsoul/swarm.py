"""群体模拟预测：心里"开个小会"——唤起一组不同性情的"内在视角"各自表态，汇成预测。

思路参考开源项目 MiroFish "Predict Anything"：以"一群有性格的智能体各自判断、再聚合"
来预测/拿主意。这里把它内化成分身脑中的一个小型议事会（乐观/谨慎/务实/重情/守护/理性），
按问题的措辞给出倾向，聚合成一个带比例的预感。纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

# (视角, 基础倾向 +1/0/-1, 它的说法)
_ARCHE = [
    ("乐观派", 1, "机会难得，我觉得能成"),
    ("谨慎派", -1, "我更担心出岔子，未必稳"),
    ("务实派", 0, "得看划不划算"),
    ("重情派", 0, "先顾着在乎的人"),
    ("守护派", 0, "护好身体和家人要紧"),
    ("理性派", 0, "讲证据、看长远"),
]
_POS = ("想", "喜欢", "机会", "好", "能成", "赚", "梦想", "期待", "值得", "开心", "顺", "把握")
_NEG = ("累", "险", "风险", "亏", "难", "怕", "担心", "危险", "熬夜", "压力", "糟", "悬", "勉强")
_RISK = ("险", "危险", "熬夜", "透支", "健康", "身体", "压力", "拼命")


def forecast(question: str) -> dict:
    q = question or ""
    pos = sum(1 for w in _POS if w in q)
    neg = sum(1 for w in _NEG if w in q)
    nudge = 1 if pos > neg else (-1 if neg > pos else 0)
    risky = any(w in q for w in _RISK)
    panel = []
    for name, base, reason in _ARCHE:
        if name == "守护派" and risky:
            base = -1
        lean = max(-1, min(1, base + nudge))
        panel.append((name, lean, reason))
    yes = sum(1 for _, l, _ in panel if l > 0)
    no = sum(1 for _, l, _ in panel if l < 0)
    neu = len(panel) - yes - no
    p = yes / (yes + no) if (yes + no) else 0.5
    say = [f"{n}说「{r}」" for n, l, r in panel if l > 0][:1] + \
          [f"{n}说「{r}」" for n, l, r in panel if l < 0][:1]
    text = (f"我在心里开了个小会（{len(panel)} 个不同的我）：{yes} 个倾向「会」、"
            f"{no} 个倾向「悬」、{neu} 个观望。综合看，大概 {int(round(p * 100))}% 能成。")
    if say:
        text += "——" + "；".join(say) + "。"
    text += "（最终还是你定。）"
    return {"p": round(p, 2), "yes": yes, "no": no, "neutral": neu, "panel": panel,
            "reasons": say, "text": text}

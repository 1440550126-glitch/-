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


def _heuristic_panel(question: str):
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
    return panel


def _llm_panel(question: str, llm):
    """让每个'我'用本地大模型真正展开表态（更接近多智能体模拟）。"""
    system = ("你脑中有六个不同性情的'我'：乐观派、谨慎派、务实派、重情派、守护派、理性派。"
              "针对问题，让每个'我'用一行表态，严格格式：视角名|会/悬/观望|一句理由。只输出六行，别的不要。")
    try:
        out = llm.chat(system, question)
    except Exception:
        return None
    panel = []
    for ln in (out or "").splitlines():
        parts = [p.strip() for p in ln.split("|")]
        if len(parts) >= 3 and parts[0]:
            stance = parts[1]
            lean = 1 if "会" in stance else (-1 if ("悬" in stance or "不" in stance) else 0)
            panel.append((parts[0], lean, "|".join(parts[2:]).strip()))
    return panel if len(panel) >= 3 else None


def _aggregate(panel) -> dict:
    yes = sum(1 for _, l, _ in panel if l > 0)
    no = sum(1 for _, l, _ in panel if l < 0)
    neu = len(panel) - yes - no
    p = yes / (yes + no) if (yes + no) else 0.5
    say = [f"{n}说「{r}」" for n, l, r in panel if l > 0 and r][:1] + \
          [f"{n}说「{r}」" for n, l, r in panel if l < 0 and r][:1]
    text = (f"我在心里开了个小会（{len(panel)} 个不同的我）：{yes} 个倾向「会」、"
            f"{no} 个倾向「悬」、{neu} 个观望。综合看，大概 {int(round(p * 100))}% 能成。")
    if say:
        text += "——" + "；".join(say) + "。"
    text += "（最终还是你定。）"
    return {"p": round(p, 2), "yes": yes, "no": no, "neutral": neu, "panel": panel,
            "reasons": say, "text": text}


def forecast(question: str, llm=None) -> dict:
    panel = None
    if llm is not None and getattr(llm, "available", False):
        panel = _llm_panel(question, llm)
    if not panel:
        panel = _heuristic_panel(question)
    return _aggregate(panel)

"""群体模拟预测：心里"开个小会"——一组不同思维模式的"我"各自表态，汇成预测。

思路参考两个开源项目：
- MiroFish "Predict Anything"：一群有性格的智能体各自判断、再聚合预测；
- ruvnet/ruv-swarm：以"认知多样性（cognitive diversity）"编排多智能体——不同思维模式协作，
  且把"意见的一致 / 分歧"本身当作信号（越一致越笃定，越分歧越该坦白没把握）。

这里内化成分身脑中的小型议事会：六种认知思维模式（发散 / 收敛 / 批判 / 系统 / 横向 / 抽象）
按问题措辞各自表态，聚合成带比例 + 多样性提示的预感。纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

# (思维模式, 基础倾向 +1/0/-1, 它的说法)；批判偏挑刺、发散/横向偏看到可能
_PATTERNS = [
    ("发散思维", 1, "能想到好几条路，机会不止一种"),
    ("收敛思维", 0, "聚焦最可能的那一条"),
    ("批判思维", -1, "我先挑毛病：风险和漏洞在哪"),
    ("系统思维", 0, "得看牵一发而动全身"),
    ("横向思维", 1, "换个角度，也许另有解法"),
    ("抽象思维", 0, "抛开细节，看长远与本质"),
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
    for name, base, reason in _PATTERNS:
        if name == "系统思维" and risky:            # 系统思维对"牵连风险"更敏感
            base = -1
        lean = max(-1, min(1, base + nudge))
        panel.append((name, lean, reason))
    return panel


def _llm_panel(question: str, llm):
    """让每个思维模式用本地大模型真正展开表态（更接近多智能体认知多样性）。"""
    names = "、".join(n for n, _, _ in _PATTERNS)
    system = (f"你脑中有六种不同的思维模式：{names}。针对问题，让每种思维各用一行表态，"
              "严格格式：思维名|会/悬/观望|一句理由。只输出六行，别的不要。")
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
    total = len(panel)
    yes = sum(1 for _, l, _ in panel if l > 0)
    no = sum(1 for _, l, _ in panel if l < 0)
    neu = total - yes - no
    p = yes / (yes + no) if (yes + no) else 0.5
    consensus = max(yes, no, neu) / total if total else 0.0   # 最大阵营占比
    diversity = round(1 - consensus, 2)                        # 越大越分歧
    if consensus >= 0.6:
        note = "（几种思路难得一致，我比较有数）"
    elif yes > 0 and no > 0 and abs(yes - no) <= 1:
        note = "（几种思路分歧不小，我也没十足把握）"
    else:
        note = ""
    say = [f"{n}说「{r}」" for n, l, r in panel if l > 0 and r][:1] + \
          [f"{n}说「{r}」" for n, l, r in panel if l < 0 and r][:1]
    text = (f"我在心里开了个小会（{total} 种不同的思路）：{yes} 个倾向「会」、"
            f"{no} 个倾向「悬」、{neu} 个观望。综合看，大概 {int(round(p * 100))}% 能成。")
    if say:
        text += "——" + "；".join(say) + "。"
    text += note + "（最终还是你定。）"
    return {"p": round(p, 2), "yes": yes, "no": no, "neutral": neu, "diversity": diversity,
            "panel": panel, "reasons": say, "text": text}


def forecast(question: str, llm=None, extra=None) -> dict:
    panel = None
    if llm is not None and getattr(llm, "available", False):
        panel = _llm_panel(question, llm)
    if not panel:
        panel = _heuristic_panel(question)
    if extra:                                   # 联邦：外部智能体作为独立思维节点入会
        panel = panel + list(extra)
    return _aggregate(panel)

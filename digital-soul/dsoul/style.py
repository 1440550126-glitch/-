"""说话风格层：让数字分身像「那个人」一样说话。

从身份设定里取口头禅 / 口吻 / 语气词，做两件事：
- style_hint：给本地大模型的"用 TA 的口吻说话"提示；
- apply_style：在降级（无大模型）回复上，轻轻加上 TA 的口头禅 / 语气词，让它依然"像本人"。

对"模仿逝者生前言行"尤为关键：哪怕没接大模型，回应也带着 TA 的口吻。纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

import random


def _persona(identity):
    return (identity or {}).get("personality", {}) or {}


def style_hint(identity) -> str:
    p = _persona(identity)
    name = (identity or {}).get("name", "我")
    bits = []
    if p.get("speaking_style"):
        bits.append(p["speaking_style"])
    cps = p.get("catchphrases") or []
    if cps:
        bits.append("常把这些挂在嘴边：" + "、".join(cps[:4]))
    parts = p.get("particles") or []
    if parts:
        bits.append("偶尔带点语气词：" + "、".join(parts[:4]))
    if not bits:
        return ""
    return f"请用「{name}」本人的口吻说话——{'；'.join(bits)}。自然就好，别刻意堆砌。"


def apply_style(text, identity, seed=None) -> str:
    """给降级回复轻轻染上 TA 的口吻：缺口头禅时补一个、句末偶尔加语气词。"""
    text = (text or "").strip()
    if not text or text.endswith(("?", "？")):       # 问句不乱加
        return text
    p = _persona(identity)
    cps = p.get("catchphrases") or []
    parts = p.get("particles") or []
    rng = random.Random(seed if seed is not None else hash(text) & 0xffffffff)
    # 已经有口头禅就不再加；否则有概率补一个开头
    if cps and not any(c in text for c in cps) and rng.random() < 0.35:
        text = cps[rng.randrange(len(cps))] + "，" + text
    # 句末偶尔加个语气词（在最后的句号前）
    if parts and rng.random() < 0.5:
        par = parts[rng.randrange(len(parts))]
        if text and text[-1] in "。.!！":
            text = text[:-1] + par + text[-1]
        else:
            text = text + par
    return text

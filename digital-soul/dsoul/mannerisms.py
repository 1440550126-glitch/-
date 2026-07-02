"""说话习惯（神似）：光记得事还不够，要"像"。

把逝者生前的说话习惯抽出来，给回复轻轻"上个色"：
- 称呼：TA 管孙子叫"乖乖"、管老伴叫"老太婆"，认人就用 TA 的叫法；
- 语气词：句尾爱带"嘛/咯/哈"，偶尔点一个，别滥用；
- 方言：把"知道→晓得""什么→啥子"这类常用词换成 TA 的说法；
- 起头/收尾：TA 爱用"我跟你讲"开头、"就这样咯"收尾。

配在 config/mannerisms.yaml，或并入 identity.speech。纯逻辑、可单测、优雅降级（没配就原样返回）。
"""

from __future__ import annotations

# 句尾已是这些就不再加语气词（避免"好啊嘛"这种叠加）
_PARTICLE_END = ("嘛", "咯", "哈", "呢", "啊", "呀", "哦", "嘞", "吧", "。", "！", "？", "…", "~")


def load_mannerisms(config=None, identity=None) -> dict:
    """汇总说话习惯：config/mannerisms.yaml 优先，并入 identity.speech，规整成统一结构。"""
    cfg = dict(config or {})
    speech = ((identity or {}).get("speech") or {}) if isinstance(identity, dict) else {}

    def _merge_list(key):
        out, seen = [], set()
        for x in list(cfg.get(key) or []) + list(speech.get(key) or []):
            s = str(x).strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
        return out

    def _merge_map(key):
        m = {}
        for src in (speech.get(key), cfg.get(key)):   # cfg 覆盖 identity
            if isinstance(src, dict):
                for k, v in src.items():
                    ks, vs = str(k).strip(), str(v).strip()
                    if ks and vs:
                        m[ks] = vs
        return m

    out = {
        "particles": _merge_list("particles"),
        "openers": _merge_list("openers"),
        "closers": _merge_list("closers"),
        "address": _merge_map("address"),
        "dialect": _merge_map("dialect"),
    }
    return out if any(out.values()) else {}        # 啥都没配就给空 dict，truthy 判断才准


def _pick(options, text):
    """从候选里挑一个——按文本长度取模，保证同一句话每次挑到同一个（可单测）。"""
    if not options:
        return None
    return options[len(text or "") % len(options)]


def address_for(mann, key) -> str | None:
    """TA 生前怎么称呼这个人（按名字或关系查），没有则 None。"""
    if not key or not mann:
        return None
    return ((mann or {}).get("address") or {}).get(str(key).strip())


def dialectize(text, mann) -> str:
    """把标准词换成 TA 的方言说法（长词先换，避免子串误伤）。"""
    if not text or not mann:
        return text or ""
    dialect = (mann or {}).get("dialect") or {}
    out = text
    for std in sorted(dialect, key=len, reverse=True):
        if std:
            out = out.replace(std, dialect[std])
    return out


def add_particle(text, mann) -> str:
    """句尾点一个 TA 爱用的语气词（已带语气词/标点则原样不动）。"""
    if not text or not mann:
        return text or ""
    particles = (mann or {}).get("particles") or []
    if not particles or text.rstrip().endswith(_PARTICLE_END):
        return text
    p = _pick(particles, text)
    return f"{text}{p}" if p else text


def apply_style(text, mann, *, particle=True) -> str:
    """给回复"上色"：先方言替换，再（可选）句尾加语气词。无配置则原样返回。"""
    if not mann:
        return text or ""
    out = dialectize(text, mann)
    if particle:
        out = add_particle(out, mann)
    return out


def opener(mann, text="") -> str | None:
    """TA 爱用的开场白（如"我跟你讲"）。"""
    return _pick((mann or {}).get("openers") or [], text)


def closer(mann, text="") -> str | None:
    """TA 爱用的收尾（如"就这样咯"）。"""
    return _pick((mann or {}).get("closers") or [], text)


def describe(mann) -> str:
    """自述说话习惯（回答"你说话有啥习惯"）。"""
    if not mann:
        return ""
    bits = []
    if mann.get("particles"):
        bits.append("说完爱带个「" + "/".join(mann["particles"][:3]) + "」")
    if mann.get("openers"):
        bits.append("开口常是「" + mann["openers"][0] + "」")
    if mann.get("dialect"):
        pairs = list(mann["dialect"].items())[:3]
        bits.append("把" + "、".join(f"「{k}」说成「{v}」" for k, v in pairs))
    if mann.get("address"):
        pairs = list(mann["address"].items())[:3]
        bits.append("管" + "、".join(f"{k}叫「{v}」" for k, v in pairs))
    return ("我说话的老习惯：" + "；".join(bits) + "。") if bits else ""

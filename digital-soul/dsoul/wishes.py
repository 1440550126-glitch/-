"""临别期许：TA 对每位家人的一句期望或祝愿。

配在 config/legacy.yaml 的 wishes:（名字→一句话），或 family 成员的 wish: 字段。
被问起（"你希望我怎样""你对我的期望"）时，由分身郑重道来。纯逻辑、可单测。
"""

from __future__ import annotations


def collect_wishes(legacy=None, family=None) -> dict:
    """汇总所有期许：{名字: 一句期望}。legacy.wishes 优先，再并入 family 成员的 wish。"""
    out: dict[str, str] = {}
    for k, v in ((legacy or {}).get("wishes", {}) or {}).items():
        if k and v:
            out[str(k)] = str(v).strip()
    try:
        from .family import members
        for m in members(family or {}):
            if m.get("wish"):
                out.setdefault(m["name"], str(m["wish"]).strip())
    except Exception:
        pass
    return out


def wish_for(wishes, name) -> str | None:
    """找给某人的期许：精确名字优先，再按包含关系（称呼/小名）模糊匹配。"""
    if not name or not wishes:
        return None
    name = str(name)
    if name in wishes:
        return wishes[name]
    for k, v in wishes.items():
        if k and (k in name or name in k):
            return v
    return None


def all_wishes(wishes) -> list:
    """把全部期许排成一句句"对谁：愿……"。"""
    return [f"对{k}：{v}" for k, v in (wishes or {}).items() if v]

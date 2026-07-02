"""居家安全：睡前陪你过一遍——门锁了吗、燃气关了吗、窗户关好没。
像家里那个总不放心的人，临睡前唠叨一圈，图个安心。纯逻辑、可单测。

清单可在 config/safety.yaml 自定义；不配就用一套通用的。
"""

from __future__ import annotations

_DEFAULT = ["门锁好了吗", "燃气灶关了吗", "窗户关好了吗", "该断电的电器断了吗"]


def checklist(config=None) -> list:
    """睡前安全清单：配置优先，否则用通用一套。"""
    items = (config or {}).get("items") if isinstance(config, dict) else None
    items = [str(x).strip() for x in (items or []) if str(x).strip()]
    return items or list(_DEFAULT)


def evening_prompt(items=None) -> str:
    """临睡前的一句叮咛（把清单串成一句）。"""
    items = items or _DEFAULT
    body = "；".join(items)
    return f"睡前我陪你过一遍：{body}？都妥了咱就安心睡。"


def is_safety_query(utterance) -> bool:
    u = utterance or ""
    return any(k in u for k in ("睡前检查", "安全检查", "锁门了吗", "关火了吗", "关煤气",
                                "睡前看一遍", "门窗", "查一遍"))


def reassure() -> str:
    return "都检查好了，安心睡，有我守着。"

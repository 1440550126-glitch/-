"""守护提醒：分身惦记着家人的健康 / 吃药 / 复查 / 重要日子，到点主动叮嘱。

config/care.yaml 配每位家人的关照项。只在本地生成提醒文本，由 daemon/语音/网页呈现，
不接触任何外部账号或设备。纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

from datetime import datetime


def _aslist(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def due_reminders(care, now=None) -> list:
    """此刻该发的守护提醒（吃药到点 / 今天该复查）。"""
    now = now or datetime.now()
    hhmm, md = now.strftime("%H:%M"), now.strftime("%m-%d")
    out = []
    for person, cfg in (care or {}).items():
        if not isinstance(cfg, dict):
            continue
        note = cfg.get("note", "")
        for t in _aslist(cfg.get("medicine")):
            if str(t).strip() == hhmm:
                out.append(f"该提醒{person}吃{note or '药'}了，别忘了。")
        c = cfg.get("checkup")
        if c and str(c).strip().replace("/", "-")[-5:] == md:
            out.append(f"今天{person}该去复查了，记得叮嘱一声。")
    return out

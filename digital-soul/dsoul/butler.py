"""贾维斯式"管家层"：态势简报 + 系统自检。

把分身的"当下状态"——在场的人、心情、今天的计划、欠账、近期领悟、子系统健康——
汇成一段管家口吻的话，随时可"汇报"。纯逻辑、零依赖、可单测。
"""

from __future__ import annotations

from datetime import datetime

_MOOD = {
    "喜": "心情不错", "怒": "有些恼火", "哀": "略有低落", "惧": "有点不安",
    "爱": "心里暖暖的", "恶": "有些不快", "欲": "想多些陪伴",
}


def _greeting(now=None) -> str:
    h = (now or datetime.now()).hour
    if h < 5:
        return "夜深了"
    if h < 11:
        return "早上好"
    if h < 14:
        return "中午好"
    if h < 18:
        return "下午好"
    return "晚上好"


def diagnostics(agent) -> dict:
    """各子系统健康快照。"""
    hub = getattr(agent, "hub", None)
    return {
        "llm": bool(agent.llm.available),
        "perception": bool(getattr(getattr(agent, "perception", None), "available", False)),
        "memory": len(agent.memory.items),
        "agents": hub.names() if hub is not None else [],
        "tasks_open": len(agent.tasks.open()) if getattr(agent, "tasks", None) else 0,
        "plan_open": len(agent.plan.open()) if getattr(agent, "plan", None) else 0,
        "mood": agent.emotions.mood()[0] if getattr(agent, "emotions", None) else None,
    }


def diagnostics_text(agent, addr: str = "您") -> str:
    d = diagnostics(agent)
    parts = [
        f"{addr}，系统自检完毕：",
        ("大模型在线" if d["llm"] else "大模型降级运行") + "，",
        ("视觉在线" if d["perception"] else "视觉离线") + "，",
        f"长期记忆 {d['memory']} 条。",
    ]
    if d["agents"]:
        parts.append(f"可调度的外部智能体：{'、'.join(d['agents'])}。")
    parts.append(f"待办 {d['tasks_open']} 项，今日计划未完成 {d['plan_open']} 项。")
    parts.append("各系统运转正常。" if d["llm"] else "建议接入本地大模型以发挥全部能力。")
    return "".join(parts)


def daily_brief(agent, present=None, addr: str = "您", now=None) -> str:
    """态势简报：当下一切要点汇成一段话。"""
    lines = [f"{_greeting(now)}，{addr}。"]
    if present:
        lines.append(f"我看到{'、'.join(present)}在身边。")
    if hasattr(agent, "memory_graph"):
        try:
            g = agent.memory_graph()
            owner = agent._owner_name() if hasattr(agent, "_owner_name") else None
            core = [n for n, _ in g.central(8)
                    if g.meta.get(n, {}).get("kind") == "person" and n != owner][:3]
            if core:
                lines.append("你最看重的人：" + "、".join(core) + "。")
        except Exception:
            pass
    if getattr(agent, "emotions", None) is not None:
        top, val = agent.emotions.mood()   # 情绪按真实时间衰减；now 仅用于问候语
        if val >= agent.emotions.baseline + 0.08:
            lines.append(f"此刻我{_MOOD.get(top, top)}。")
    plan_open = [it.get("text", "") for it in agent.plan.open()] if getattr(agent, "plan", None) else []
    if plan_open:
        lines.append("今天打算做这几件事：" + "；".join(plan_open) + "。")
    topen = agent.tasks.open() if getattr(agent, "tasks", None) else []
    if topen:
        heads = "、".join(t.get("instruction", "") for t in topen[:3])
        lines.append(f"另外还有 {len(topen)} 件事欠着：{heads}。")
    refl = agent.recent_reflections(1) if hasattr(agent, "recent_reflections") else []
    if refl:
        lines.append("我最近的一点体会：" + refl[0])
    if len(lines) == 1:
        lines.append("一切如常，没有需要您操心的事。")
    return " ".join(lines)

"""多步任务编排（贾维斯："订明天的会议并通知大家"）。

把一句含多个动作的指令拆成几步，逐步路由到最合适的执行者——
设备控制 / 外部智能体 / 兜底提醒——再把结果汇总成一段话。
拆分是纯函数、可单测；执行复用 Agent 既有的设备与派活通道（含授权）。
"""

from __future__ import annotations

import re

from .devices import parse_device_command
from .remote_agents import parse_dispatch

_SPLIT = r"，|,|、|；|;|然后|接着|再帮我|再|并且|并|顺便|还要|还得"
# 可被委派给外部智能体的动作动词
_VERBS = ("订", "预订", "预约", "通知", "告诉", "查", "查询", "发", "买", "购", "安排",
          "提醒", "写", "做", "取消", "回复", "下单", "整理", "打包", "备份", "生成")


def split_steps(text: str) -> list[str]:
    parts = re.split(_SPLIT, text or "")
    return [p.strip(" 。.!！?？") for p in parts if p and p.strip(" 。.!！?？")]


def _actionable(agent, step: str) -> bool:
    if getattr(agent, "devices", None) is not None and parse_device_command(step):
        return True
    hub = getattr(agent, "hub", None)
    if hub is not None and hub.names():
        if parse_dispatch(step, hub.names()):
            return True
        if any(v in step for v in _VERBS):
            return True
    return False


def orchestrate(agent, speaker, instruction, addr: str = "您"):
    """多步则执行并汇总；单步（或没有可执行项）返回 None，交回普通流程。

    先判定可执行步数，确认 ≥2 步才真正执行——避免单步在判定时被误执行。
    """
    steps = [s for s in split_steps(instruction) if _actionable(agent, s)]
    if len(steps) < 2:
        return None
    done = [(s, agent._exec_one_step(speaker, s)) for s in steps]
    body = "\n".join(f"· {s} → {m}" for s, m in done)
    return f"好的，{addr}，这几件事我都办了：\n{body}"

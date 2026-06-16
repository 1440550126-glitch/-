"""离线兜底 provider：没有任何大模型 Key 也能跑起整个系统。

它不"思考"，而是做确定性的有用响应：复述意图、回显记忆上下文、引导配置真模型。
同时支持极简指令（echo/记住），让工具循环与记忆在零配置下也能演示与测试。
"""
from __future__ import annotations

import re

from .base import Message, Provider


class OfflineProvider(Provider):
    name = "offline"

    def chat(self, messages, *, temperature=0.7, max_tokens=2048) -> str:
        # 工具刚执行完（上一条是工具返回）→ 给出最终确认，避免重复发起同一工具
        if messages and messages[-1].role == "tool":
            return f"好的，已完成。{messages[-1].content[:120]}"

        user = ""
        for m in reversed(messages):
            if m.role == "user":
                user = m.content
                break

        # 极简内置技能，保证零配置可演示工具/记忆链路
        m_echo = re.match(r"^\s*echo[:：]?\s*(.+)$", user, re.S)
        if m_echo:
            return m_echo.group(1).strip()

        m_remember = re.match(r"^\s*(?:记住|remember)[:：]?\s*(.+)$", user, re.S)
        if m_remember:
            fact = m_remember.group(1).strip()
            return ('```tool\n{"name": "remember", "args": {"text": "%s"}}\n```'
                    % fact.replace('"', "'"))

        return (
            "（离线模式）我已收到："
            f"「{user[:120]}」。\n"
            "当前未配置大模型，仅做基础响应。配置任意大模型即可解锁完整推理与工具能力：\n"
            "  export ANTHROPIC_API_KEY=...    # 或\n"
            "  export OPENAI_API_KEY=... OPENAI_BASE_URL=...   # DeepSeek/Kimi/通义 等\n"
            "  或启动本地 Ollama（mnemo 会自动接入）。"
        )

    def available(self) -> bool:
        return True

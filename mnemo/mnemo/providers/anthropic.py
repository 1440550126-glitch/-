"""Anthropic Claude provider（/v1/messages）。"""
from __future__ import annotations

from .base import Message, Provider, ProviderError, http_post_json


def _normalize(messages: list[Message]) -> tuple[str, list[dict]]:
    """拆出 system；把 tool 角色降级为 user；合并相邻同角色；确保以 user 开头。"""
    system_parts: list[str] = []
    conv: list[dict] = []
    for m in messages:
        if m.role == "system":
            system_parts.append(m.content)
            continue
        role = "assistant" if m.role == "assistant" else "user"
        text = m.content if m.role != "tool" else f"[工具 {m.name} 返回]\n{m.content}"
        if conv and conv[-1]["role"] == role:
            conv[-1]["content"] += "\n\n" + text
        else:
            conv.append({"role": role, "content": text})
    if conv and conv[0]["role"] != "user":
        conv.insert(0, {"role": "user", "content": "(继续)"})
    return "\n\n".join(system_parts), conv


class AnthropicProvider(Provider):
    name = "anthropic"

    def chat(self, messages, *, temperature=0.7, max_tokens=2048) -> str:
        if not self.api_key:
            raise ProviderError("缺少 ANTHROPIC_API_KEY")
        system, conv = _normalize(messages)
        url = f"{self.base_url or 'https://api.anthropic.com'}/v1/messages"
        payload = {
            "model": self.model or "claude-opus-4-8",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": conv,
        }
        if system:
            payload["system"] = system
        resp = http_post_json(url, payload, headers={
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        })
        parts = resp.get("content", [])
        return "".join(p.get("text", "") for p in parts if p.get("type") == "text").strip()

    def available(self) -> bool:
        return bool(self.api_key)

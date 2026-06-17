"""Anthropic Claude provider（/v1/messages）。"""
from __future__ import annotations

import json

from .base import Message, Provider, ProviderError, http_post_json, http_post_sse


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
    DEFAULT_MODEL = "claude-opus-4-8"
    # 这些模型仅接受默认 temperature（=1），发送非默认值会 400
    _FIXED_TEMP = ("opus-4-8", "opus-4-7")

    def _model(self) -> str:
        return self.model or self.DEFAULT_MODEL

    def _maybe_temp(self, payload: dict, temperature: float) -> None:
        if not any(m in self._model() for m in self._FIXED_TEMP):
            payload["temperature"] = temperature

    def chat(self, messages, *, temperature=0.7, max_tokens=2048) -> str:
        if not self.api_key:
            raise ProviderError("缺少 ANTHROPIC_API_KEY")
        system, conv = _normalize(messages)
        url = f"{self.base_url or 'https://api.anthropic.com'}/v1/messages"
        payload = {
            "model": self._model(),
            "max_tokens": max_tokens,
            "messages": conv,
        }
        self._maybe_temp(payload, temperature)
        if system:
            payload["system"] = system
        resp = http_post_json(url, payload, headers={
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        })
        self._capture_usage(resp)
        parts = resp.get("content", [])
        return "".join(p.get("text", "") for p in parts if p.get("type") == "text").strip()

    def _capture_usage(self, resp: dict) -> None:
        u = resp.get("usage") or {}
        self.last_usage = ({"in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0)}
                           if u else None)

    def stream(self, messages, *, temperature=0.7, max_tokens=2048):
        if not self.api_key:
            raise ProviderError("缺少 ANTHROPIC_API_KEY")
        system, conv = _normalize(messages)
        url = f"{self.base_url or 'https://api.anthropic.com'}/v1/messages"
        payload = {"model": self._model(), "max_tokens": max_tokens,
                   "messages": conv, "stream": True}
        self._maybe_temp(payload, temperature)
        if system:
            payload["system"] = system
        for data in http_post_sse(url, payload, headers={
                "x-api-key": self.api_key, "anthropic-version": "2023-06-01"}):
            if not data or data == "[DONE]":
                continue
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            if obj.get("type") == "content_block_delta":
                delta = obj.get("delta", {})
                if delta.get("type") == "text_delta" and delta.get("text"):
                    yield delta["text"]
            elif obj.get("type") == "error":
                raise ProviderError(f"Anthropic 流式错误：{obj.get('error')}")

    def available(self) -> bool:
        return bool(self.api_key)

    def supports_tools(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def _to_native(messages):
        system, conv = [], []
        for m in messages:
            if m.role == "system":
                system.append(m.content)
            elif m.role == "assistant" and m.tool_calls:
                blocks = ([{"type": "text", "text": m.content}] if m.content else [])
                for tc in m.tool_calls:
                    blocks.append({"type": "tool_use", "id": tc["id"],
                                   "name": tc["name"], "input": tc["args"]})
                conv.append({"role": "assistant", "content": blocks})
            elif m.role == "tool":
                conv.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": m.tool_call_id or m.name,
                     "content": m.content}]})
            else:
                conv.append({"role": "assistant" if m.role == "assistant" else "user",
                             "content": m.content})
        return "\n\n".join(system), conv

    def supports_vision(self) -> bool:
        return bool(self.api_key)

    def vision(self, image_path, prompt="描述这张图片") -> str:
        import base64
        import mimetypes
        from pathlib import Path
        if not self.api_key:
            raise ProviderError("缺少 ANTHROPIC_API_KEY")
        data = base64.b64encode(Path(image_path).read_bytes()).decode()
        mime = mimetypes.guess_type(image_path)[0] or "image/png"
        payload = {"model": self.model or "claude-opus-4-8", "max_tokens": 1024, "messages": [
            {"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}},
                {"type": "text", "text": prompt}]}]}
        resp = http_post_json(f"{self.base_url or 'https://api.anthropic.com'}/v1/messages",
                              payload, headers={"x-api-key": self.api_key,
                                                "anthropic-version": "2023-06-01"})
        return "".join(b.get("text", "") for b in resp.get("content", [])
                       if b.get("type") == "text").strip()

    def chat_tools(self, messages, tool_specs, *, temperature=0.7, max_tokens=2048) -> dict:
        if not self.api_key:
            raise ProviderError("缺少 ANTHROPIC_API_KEY")
        system, conv = self._to_native(messages)
        tools = [{"name": s["name"], "description": s["description"],
                  "input_schema": {"type": "object",
                                   "properties": {k: {"type": "string", "description": v}
                                                  for k, v in s["parameters"].items()},
                                   "required": []}} for s in tool_specs]
        payload = {"model": self._model(), "max_tokens": max_tokens,
                   "messages": conv, "tools": tools}
        self._maybe_temp(payload, temperature)
        if system:
            payload["system"] = system
        resp = http_post_json(f"{self.base_url or 'https://api.anthropic.com'}/v1/messages",
                              payload, headers={"x-api-key": self.api_key,
                                                "anthropic-version": "2023-06-01"})
        self._capture_usage(resp)
        text, calls = "", []
        for block in resp.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
            elif block.get("type") == "tool_use":
                calls.append({"id": block.get("id"), "name": block.get("name"),
                              "args": block.get("input") or {}})
        return {"text": text.strip(), "tool_calls": calls}

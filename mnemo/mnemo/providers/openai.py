"""OpenAI 兼容 provider（/chat/completions）。

兼容一切 OpenAI 风格接口：OpenAI、DeepSeek、Kimi、通义百炼、火山方舟、
本地 vLLM/LM Studio 等——改 base_url + model 即可。
"""
from __future__ import annotations

import json

from .base import Message, Provider, ProviderError, http_post_json, http_post_sse


class OpenAIProvider(Provider):
    name = "openai"

    def _messages(self, messages: list[Message]) -> list[dict]:
        return [m.to_openai() for m in messages]

    def chat(self, messages, *, temperature=0.7, max_tokens=2048) -> str:
        if not self.api_key:
            raise ProviderError("缺少 OPENAI_API_KEY（OpenAI 兼容接口）")
        url = f"{self.base_url or 'https://api.openai.com/v1'}/chat/completions"
        payload = {
            "model": self.model or "gpt-4o-mini",
            "messages": self._messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = http_post_json(url, payload, headers={
            "Authorization": f"Bearer {self.api_key}",
        })
        choices = resp.get("choices") or []
        if not choices:
            raise ProviderError(f"无返回：{str(resp)[:300]}")
        self._capture_usage(resp)
        return (choices[0].get("message", {}).get("content") or "").strip()

    def _capture_usage(self, resp: dict) -> None:
        u = resp.get("usage") or {}
        self.last_usage = ({"in": u.get("prompt_tokens", 0), "out": u.get("completion_tokens", 0)}
                           if u else None)

    def stream(self, messages, *, temperature=0.7, max_tokens=2048):
        if not self.api_key:
            raise ProviderError("缺少 OPENAI_API_KEY（OpenAI 兼容接口）")
        url = f"{self.base_url or 'https://api.openai.com/v1'}/chat/completions"
        payload = {
            "model": self.model or "gpt-4o-mini",
            "messages": self._messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        for data in http_post_sse(url, payload, headers={
                "Authorization": f"Bearer {self.api_key}"}):
            if not data or data == "[DONE]":
                continue
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = obj.get("choices") or []
            if choices:
                piece = choices[0].get("delta", {}).get("content")
                if piece:
                    yield piece

    def embed(self, texts: list[str]):
        if not self.api_key:
            return None
        url = f"{self.base_url or 'https://api.openai.com/v1'}/embeddings"
        try:
            resp = http_post_json(url, {
                "model": self.extra.get("embed_model", "text-embedding-3-small"),
                "input": texts,
            }, headers={"Authorization": f"Bearer {self.api_key}"})
            return [d["embedding"] for d in resp.get("data", [])]
        except ProviderError:
            return None

    def available(self) -> bool:
        return bool(self.api_key)

    def supports_tools(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def _to_native(messages: list[Message]) -> list[dict]:
        out = []
        for m in messages:
            if m.role == "tool":
                out.append({"role": "tool", "tool_call_id": m.tool_call_id or m.name,
                            "content": m.content})
            elif m.role == "assistant" and m.tool_calls:
                out.append({"role": "assistant", "content": m.content or None,
                            "tool_calls": [
                                {"id": tc["id"], "type": "function",
                                 "function": {"name": tc["name"],
                                              "arguments": json.dumps(tc["args"], ensure_ascii=False)}}
                                for tc in m.tool_calls]})
            else:
                out.append({"role": m.role, "content": m.content})
        return out

    @staticmethod
    def _tool_schema(specs: list[dict]) -> list[dict]:
        return [{"type": "function", "function": {
            "name": s["name"], "description": s["description"],
            "parameters": {"type": "object",
                           "properties": {k: {"type": "string", "description": v}
                                          for k, v in s["parameters"].items()},
                           "required": []}}} for s in specs]

    def supports_vision(self) -> bool:
        return bool(self.api_key)

    def vision(self, image_path, prompt="描述这张图片") -> str:
        import base64
        import mimetypes
        from pathlib import Path
        if not self.api_key:
            raise ProviderError("缺少 OPENAI_API_KEY")
        data = base64.b64encode(Path(image_path).read_bytes()).decode()
        mime = mimetypes.guess_type(image_path)[0] or "image/png"
        url = f"{self.base_url or 'https://api.openai.com/v1'}/chat/completions"
        payload = {"model": self.model or "gpt-4o-mini", "max_tokens": 1024, "messages": [
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}]}]}
        resp = http_post_json(url, payload, headers={"Authorization": f"Bearer {self.api_key}"})
        return ((resp.get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()

    def chat_tools(self, messages, tool_specs, *, temperature=0.7, max_tokens=2048) -> dict:
        if not self.api_key:
            raise ProviderError("缺少 OPENAI_API_KEY")
        url = f"{self.base_url or 'https://api.openai.com/v1'}/chat/completions"
        payload = {
            "model": self.model or "gpt-4o-mini",
            "messages": self._to_native(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tools": self._tool_schema(tool_specs),
            "tool_choice": "auto",
        }
        resp = http_post_json(url, payload, headers={"Authorization": f"Bearer {self.api_key}"})
        self._capture_usage(resp)
        msg = (resp.get("choices") or [{}])[0].get("message", {})
        calls = []
        for tc in (msg.get("tool_calls") or []):
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append({"id": tc.get("id"), "name": fn.get("name"), "args": args})
        return {"text": msg.get("content") or "", "tool_calls": calls}

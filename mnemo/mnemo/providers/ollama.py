"""Ollama 本地模型 provider（/api/chat）。完全离线、无需联网/密钥。"""
from __future__ import annotations

import urllib.request

from .base import Message, Provider, ProviderError, http_post_json


class OllamaProvider(Provider):
    name = "ollama"

    def chat(self, messages, *, temperature=0.7, max_tokens=2048) -> str:
        base = self.base_url or "http://localhost:11434"
        payload = {
            "model": self.model or "llama3.1",
            "messages": [{"role": m.role if m.role != "tool" else "user",
                          "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        resp = http_post_json(f"{base}/api/chat", payload)
        return (resp.get("message", {}).get("content") or "").strip()

    def available(self) -> bool:
        base = self.base_url or "http://localhost:11434"
        try:
            with urllib.request.urlopen(f"{base}/api/tags", timeout=1) as r:
                return r.status == 200
        except Exception:
            return False

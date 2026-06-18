"""Ollama 本地模型 provider（/api/chat）。完全离线、无需联网/密钥。"""
from __future__ import annotations

import json
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
        """服务可达 **且** 所选模型已 pull。否则在 auto 选择时让位给其它后端/离线，
        避免选中 Ollama 后才在 chat 时因模型缺失而失败。"""
        base = self.base_url or "http://localhost:11434"
        want = self.model or "llama3.1"
        try:
            with urllib.request.urlopen(f"{base}/api/tags", timeout=1) as r:
                if r.status != 200:
                    return False
                data = json.loads(r.read().decode("utf-8", "replace"))
        except Exception:
            return False
        names = [m.get("name", "") for m in (data.get("models") or [])]
        # Ollama 标签常带 :tag（如 llama3.1:latest）；允许名字/前缀匹配
        return any(n == want or n.split(":")[0] == want.split(":")[0] for n in names)

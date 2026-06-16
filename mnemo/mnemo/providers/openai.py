"""OpenAI 兼容 provider（/chat/completions）。

兼容一切 OpenAI 风格接口：OpenAI、DeepSeek、Kimi、通义百炼、火山方舟、
本地 vLLM/LM Studio 等——改 base_url + model 即可。
"""
from __future__ import annotations

from .base import Message, Provider, ProviderError, http_post_json


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
        return (choices[0].get("message", {}).get("content") or "").strip()

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

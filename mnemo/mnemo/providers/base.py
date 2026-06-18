"""Provider 抽象层：统一的消息格式与 chat 接口，让上层与具体大模型解耦。

只要求 provider 实现「文本进、文本出」的 chat()，工具调用由 agent 层用
通用文本协议实现——这样任何能输出文本的模型（含本地/开源）都能用上工具。
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, Optional


class ProviderError(Exception):
    """Provider 调用失败（网络、鉴权、配额等）。"""


# 可重试的瞬时 HTTP 状态（限流 / 网关 / 服务暂不可用）——为 7×24 无人值守增加韧性
_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


def _open_with_retry(req, timeout: int, retries: int, url: str):
    """对瞬时网络错误/5xx 做指数退避重试；4xx（鉴权/参数）不重试，立即抛出。"""
    delay = 1.0
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            last = ProviderError(f"HTTP {e.code} @ {url}: {body[:600]}")
            if e.code in _RETRYABLE_STATUS and attempt < retries:
                time.sleep(delay); delay *= 2; continue
            raise last from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            reason = getattr(e, "reason", e)
            last = ProviderError(f"网络错误 @ {url}: {reason}")
            if attempt < retries:
                time.sleep(delay); delay *= 2; continue
            raise last from e
    raise last or ProviderError(f"请求失败 @ {url}")  # 理论不可达


@dataclass
class Message:
    role: str  # system | user | assistant | tool
    content: str
    name: Optional[str] = None        # tool 角色时为工具名
    tool_calls: Optional[list] = None  # assistant 原生工具调用 [{id,name,args}]
    tool_call_id: Optional[str] = None  # tool 结果对应的调用 id（原生）

    def to_openai(self) -> dict:
        d = {"role": "tool" if self.role == "tool" else self.role, "content": self.content}
        if self.role == "tool":
            # OpenAI 工具结果需要 tool_call_id；我们用文本协议，降级为 user 角色更通用
            d = {"role": "user", "content": f"[工具 {self.name} 返回]\n{self.content}"}
        return d


def http_post_json(url: str, payload: dict, headers: dict | None = None,
                   timeout: int = 120, retries: int = 2) -> dict:
    """标准库实现的 JSON POST（含瞬时错误重试），避免引入 requests 等第三方依赖。"""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with _open_with_retry(req, timeout, retries, url) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_post_sse(url: str, payload: dict, headers: dict | None = None,
                  timeout: int = 300, retries: int = 2) -> Iterator[str]:
    """标准库实现的 SSE 流式 POST：逐条产出 `data:` 行的内容（已去前缀）。

    仅对建连阶段重试；一旦开始接收流则不再中途重试（语义安全）。
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    resp = _open_with_retry(req, timeout, retries, url)
    with resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if line.startswith("data:"):
                yield line[5:].strip()


class Provider(ABC):
    name: str = "base"

    def __init__(self, model: str | None = None, api_key: str | None = None,
                 base_url: str | None = None, **kw):
        self.model = model
        self.api_key = api_key
        self.base_url = (base_url or "").rstrip("/")
        self.extra = kw
        # 最近一次调用的真实用量 {"in": int, "out": int}；拿不到则为 None（上层会估算）
        self.last_usage: dict | None = None

    @abstractmethod
    def chat(self, messages: list[Message], *, temperature: float = 0.7,
             max_tokens: int = 2048) -> str:
        """同步返回模型的完整文本回复。"""

    def stream(self, messages: list[Message], *, temperature: float = 0.7,
               max_tokens: int = 2048) -> Iterator[str]:
        """流式产出文本增量。默认退化为一次性产出完整结果，
        因此所有后端无需改动即可被流式接口调用。"""
        yield self.chat(messages, temperature=temperature, max_tokens=max_tokens)

    def available(self) -> bool:
        """是否具备调用条件（有 key / 服务可达）。auto 选择时据此筛选。"""
        return True

    def supports_tools(self) -> bool:
        """是否支持原生 function-calling。不支持则上层用文本工具协议。"""
        return False

    def chat_tools(self, messages: list[Message], tool_specs: list[dict], *,
                   temperature: float = 0.7, max_tokens: int = 2048) -> dict:
        """原生工具调用。返回 {"text": str, "tool_calls": [{id,name,args}]}。

        tool_specs: [{"name","description","parameters": {名: 说明}}]
        """
        raise NotImplementedError

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        """可选：返回向量。不支持则返回 None（记忆检索会回退到关键词）。"""
        return None

    def supports_vision(self) -> bool:
        """是否支持图像理解（多模态）。"""
        return False

    def vision(self, image_path: str, prompt: str = "描述这张图片") -> str:
        """对一张本地图片做视觉问答，返回文本。"""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<Provider {self.name} model={self.model}>"

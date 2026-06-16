"""Provider 抽象层：统一的消息格式与 chat 接口，让上层与具体大模型解耦。

只要求 provider 实现「文本进、文本出」的 chat()，工具调用由 agent 层用
通用文本协议实现——这样任何能输出文本的模型（含本地/开源）都能用上工具。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


class ProviderError(Exception):
    """Provider 调用失败（网络、鉴权、配额等）。"""


@dataclass
class Message:
    role: str  # system | user | assistant | tool
    content: str
    name: Optional[str] = None  # tool 角色时为工具名

    def to_openai(self) -> dict:
        d = {"role": "tool" if self.role == "tool" else self.role, "content": self.content}
        if self.role == "tool":
            # OpenAI 工具结果需要 tool_call_id；我们用文本协议，降级为 user 角色更通用
            d = {"role": "user", "content": f"[工具 {self.name} 返回]\n{self.content}"}
        return d


def http_post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 120) -> dict:
    """标准库实现的 JSON POST，避免引入 requests 等第三方依赖。"""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise ProviderError(f"HTTP {e.code} @ {url}: {body[:600]}") from e
    except urllib.error.URLError as e:
        raise ProviderError(f"网络错误 @ {url}: {e.reason}") from e
    except (TimeoutError, OSError) as e:
        raise ProviderError(f"连接失败 @ {url}: {e}") from e


class Provider(ABC):
    name: str = "base"

    def __init__(self, model: str | None = None, api_key: str | None = None,
                 base_url: str | None = None, **kw):
        self.model = model
        self.api_key = api_key
        self.base_url = (base_url or "").rstrip("/")
        self.extra = kw

    @abstractmethod
    def chat(self, messages: list[Message], *, temperature: float = 0.7,
             max_tokens: int = 2048) -> str:
        """同步返回模型的完整文本回复。"""

    def available(self) -> bool:
        """是否具备调用条件（有 key / 服务可达）。auto 选择时据此筛选。"""
        return True

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        """可选：返回向量。不支持则返回 None（记忆检索会回退到关键词）。"""
        return None

    def __repr__(self) -> str:
        return f"<Provider {self.name} model={self.model}>"

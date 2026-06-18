"""Provider 注册表与工厂：provider=auto 时按优先级自动挑选可用后端。

插件可调用 register_provider() 注入自定义后端，实现"接入任何大模型"。
"""
from __future__ import annotations

from ..config import Config
from .anthropic import AnthropicProvider
from .base import Message, Provider, ProviderError
from .gemini import GeminiProvider
from .offline import OfflineProvider
from .ollama import OllamaProvider
from .openai import OpenAIProvider

REGISTRY: dict[str, type[Provider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
    "offline": OfflineProvider,
}

# auto 选择优先级：能力强的在前，离线兜底在最后
AUTO_ORDER = ["anthropic", "openai", "gemini", "ollama", "offline"]


def register_provider(name: str, cls: type[Provider]) -> None:
    REGISTRY[name] = cls
    if name not in AUTO_ORDER:
        AUTO_ORDER.insert(-1, name)


def _construct(name: str, cfg: Config) -> Provider:
    pc = cfg.provider_conf(name)
    model = cfg.get("model") or pc.get("model")
    return REGISTRY[name](
        model=model,
        api_key=pc.get("api_key"),
        base_url=pc.get("base_url"),
        **{k: v for k, v in pc.items() if k not in {"model", "api_key", "base_url"}},
    )


def build_provider(cfg: Config) -> Provider:
    name = (cfg.get("provider") or "auto").lower()
    if name != "auto":
        if name not in REGISTRY:
            raise ProviderError(f"未知 provider：{name}（可用：{', '.join(REGISTRY)}）")
        return _construct(name, cfg)
    for cand in AUTO_ORDER:
        try:
            p = _construct(cand, cfg)
            if p.available():
                return p
        except Exception:
            continue
    return OfflineProvider()


def provider_status(cfg: Config) -> list[dict]:
    """供 CLI 展示各后端是否就绪。"""
    out = []
    for name in AUTO_ORDER:
        try:
            p = _construct(name, cfg)
            out.append({"name": name, "model": p.model, "available": p.available()})
        except Exception as e:  # noqa: BLE001
            out.append({"name": name, "model": None, "available": False, "error": str(e)})
    return out


__all__ = ["Message", "Provider", "ProviderError", "build_provider",
           "provider_status", "register_provider", "REGISTRY"]

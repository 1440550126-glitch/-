"""大模型接口（推理引擎 / "大脑"）：支持多模型、多服务商、按任务路由。

- 默认对接本地 Ollama（https://ollama.com）：在 16G 内存机器上
      ollama pull qwen2.5:7b-instruct
- 也支持任何 OpenAI 兼容端点（llama.cpp / LM Studio / vLLM / 云 API），provider="openai"。
- LLMRouter：按"任务/场景"选不同模型；panel 让群体小会的不同思路各用一个模型（认知多样性）。
没有可用大模型时自动降级（available=False），由 Agent 用记忆拼朴素回复——任何机器都能先跑起来。
配置见 config/models.yaml；也可用环境变量 DSOUL_LLM_MODEL / DSOUL_LLM_HOST / DSOUL_LLM_KEY 覆盖。
"""

from __future__ import annotations

import json
import os
import re
import urllib.request

DEFAULT_MODEL = os.environ.get("DSOUL_LLM_MODEL", "qwen2.5:7b-instruct")
DEFAULT_HOST = os.environ.get("DSOUL_LLM_HOST", "http://localhost:11434")

# 推理模型（Qwen3 / Gemma 等）会先输出一段 <think>…</think> 思考，再给答案。
# 这块思考不该展示给家人，要剥掉，只留最终回答。
_THINK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)


def strip_think(text: str) -> str:
    """剥掉推理模型输出里的 <think>…</think> 思考块，只留最终回答。"""
    if not text:
        return text or ""
    out = _THINK_RE.sub("", text)
    if "</think>" in out:                 # 开标签在更早的分片里、只剩闭标签：取其后的答案
        out = out.split("</think>")[-1]
    out = re.sub(r"</?think>", "", out)   # 去掉任何残留标签
    return out.strip()


class LLM:
    def __init__(self, model: str | None = None, host: str | None = None,
                 provider: str = "ollama", api_key: str | None = None,
                 temperature: float = 0.8) -> None:
        self.provider = provider
        self.model = model or DEFAULT_MODEL
        self.host = (host or DEFAULT_HOST).rstrip("/")
        self.api_key = api_key or os.environ.get("DSOUL_LLM_KEY")
        self.temperature = temperature
        self.available = self._ping()

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _ping(self) -> bool:
        try:
            path = "/api/tags" if self.provider == "ollama" else "/models"
            urllib.request.urlopen(
                urllib.request.Request(self.host + path, headers=self._headers()), timeout=1.5)
            return True
        except Exception:
            return False

    def _post(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            self.host + path, data=json.dumps(payload).encode("utf-8"), headers=self._headers())
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def chat(self, system: str, user: str) -> str:
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        if self.provider == "ollama":
            data = self._post("/api/chat", {"model": self.model, "messages": msgs,
                                            "stream": False, "options": {"temperature": self.temperature}})
            return strip_think(data["message"]["content"].strip())
        # OpenAI 兼容（host 应含 /v1，如 http://localhost:1234/v1）
        data = self._post("/chat/completions", {"model": self.model, "messages": msgs,
                                                "temperature": self.temperature})
        return strip_think(data["choices"][0]["message"]["content"].strip())


def _llm_from(spec) -> LLM:
    spec = spec or {}
    return LLM(model=spec.get("model"), host=spec.get("host"),
               provider=spec.get("provider", "ollama"), api_key=spec.get("api_key"))


class LLMRouter:
    """按任务选模型；panel 提供一组模型给群体小会用（不同模型 = 认知多样性）。"""

    def __init__(self, default: LLM, tasks=None, panel=None) -> None:
        self.default = default
        self.tasks = tasks or {}
        self._panel = panel or []

    def for_task(self, task: str) -> LLM:
        return self.tasks.get(task, self.default)

    def panel(self) -> list:
        return self._panel


def build_router(config=None, model_override: str | None = None) -> LLMRouter:
    config = config or {}
    default = LLM(model=model_override) if model_override else _llm_from(config.get("default"))
    tasks = {k: _llm_from(v) for k, v in (config.get("tasks") or {}).items()}
    panel = [_llm_from(s) for s in (config.get("panel") or [])]
    return LLMRouter(default, tasks, panel)

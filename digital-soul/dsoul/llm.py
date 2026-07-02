"""大模型接口（推理引擎 / "大脑"）：支持多模型、多服务商、按任务路由。

- 默认对接本地 Ollama（https://ollama.com）：在 16G 内存机器上
      ollama pull qwen2.5:7b-instruct
- 也支持任何 OpenAI 兼容端点（llama.cpp / LM Studio / vLLM / 云 API），provider="openai"。
- 也可对接 MiniMax 云端大模型，provider="minimax"（中文强、可配声音克隆；私密记忆建议仍走本地）。
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

# MiniMax（付费云、中文与声音质量很顶）：对话用 OpenAI 兼容的 /text/chatcompletion_v2 端点，
# 但没有 /models 列表接口——单列为一个 provider。密钥只从环境变量读（DSOUL_LLM_KEY 或 MINIMAX_API_KEY），绝不入库。
MINIMAX_HOST = "https://api.minimax.io/v1"        # 国际站；国内：https://api.minimaxi.com/v1
MINIMAX_MODEL = "MiniMax-Text-01"                 # 也可 abab6.5s-chat / MiniMax-M1 等
MINIMAX_CHAT_PATH = "/text/chatcompletion_v2"

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
        if provider == "minimax":                       # MiniMax 云端：自带合理默认，密钥可与 TTS 共用
            self.model = model or os.environ.get("DSOUL_LLM_MODEL") or MINIMAX_MODEL
            self.host = (host or os.environ.get("DSOUL_LLM_HOST") or MINIMAX_HOST).rstrip("/")
            self.api_key = api_key or os.environ.get("DSOUL_LLM_KEY") or os.environ.get("MINIMAX_API_KEY")
        else:
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
        if self.provider == "minimax":
            return bool(self.api_key)     # 云端付费、无 /models 列表：有密钥即视为可用；真出错时 chat() 抛异常、上层兜底降级
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
        # OpenAI 兼容（host 应含 /v1）；MiniMax 用自家路径 /text/chatcompletion_v2
        path = MINIMAX_CHAT_PATH if self.provider == "minimax" else "/chat/completions"
        data = self._post(path, {"model": self.model, "messages": msgs, "temperature": self.temperature})
        choices = data.get("choices") or []
        if not choices:                          # MiniMax 出错时 choices 为空、错误码在 base_resp 里
            br = data.get("base_resp") or {}
            raise RuntimeError(f"模型无回复 base_resp={br.get('status_code')}：{br.get('status_msg')}"
                               if br else "模型无回复")
        return strip_think((choices[0].get("message", {}).get("content") or "").strip())


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

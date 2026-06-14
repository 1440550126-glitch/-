"""本地大模型接口（推理引擎 / "大脑"）。

默认对接 Ollama（https://ollama.com）——在 16G 内存机器上：
    ollama pull qwen2.5:7b-instruct      # 4-bit 量化，约 5-6GB，可跑
没装 Ollama 时自动降级（available=False），由 Agent 用记忆拼一个朴素回复，
保证整套框架在任何机器上都能先跑起来。
"""

from __future__ import annotations

import json
import os
import urllib.request

# 部署时可用环境变量覆盖（例如把大模型跑在局域网另一台机器上）：
#   DSOUL_LLM_HOST=http://192.168.1.10:11434
#   DSOUL_LLM_MODEL=qwen2.5:3b-instruct
DEFAULT_MODEL = os.environ.get("DSOUL_LLM_MODEL", "qwen2.5:7b-instruct")
DEFAULT_HOST = os.environ.get("DSOUL_LLM_HOST", "http://localhost:11434")


class LLM:
    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
    ) -> None:
        self.model = model or DEFAULT_MODEL
        self.host = (host or DEFAULT_HOST).rstrip("/")
        self.available = self._ping()

    def _ping(self) -> bool:
        try:
            urllib.request.urlopen(self.host + "/api/tags", timeout=1)
            return True
        except Exception:
            return False

    def chat(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": 0.8},
        }
        req = urllib.request.Request(
            self.host + "/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["message"]["content"].strip()

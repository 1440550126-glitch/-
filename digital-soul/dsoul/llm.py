"""本地大模型接口（推理引擎 / "大脑"）。

默认对接 Ollama（https://ollama.com）——在 16G 内存机器上：
    ollama pull qwen2.5:7b-instruct      # 4-bit 量化，约 5-6GB，可跑
没装 Ollama 时自动降级（available=False），由 Agent 用记忆拼一个朴素回复，
保证整套框架在任何机器上都能先跑起来。
"""

from __future__ import annotations

import json
import urllib.request


class LLM:
    def __init__(
        self,
        model: str = "qwen2.5:7b-instruct",
        host: str = "http://localhost:11434",
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
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

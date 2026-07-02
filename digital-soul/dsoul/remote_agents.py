"""隔空控制外部智能体（如"爱马仕"/"openclaw"）。

机器人是"大脑"，把活儿通过网络（HTTP）派给跑在笔记本 / 苹果主机上的智能体执行，
执行完把结果回传。任何监听 `POST /task` 的智能体都能接（参考实现见
scripts/agent_worker.py）。端点配置见 config/agents.yaml，可用环境变量覆盖。
"""

from __future__ import annotations

import json
import os
import urllib.request


DISPATCH_VERBS = (
    "让", "叫", "请", "帮", "派", "用", "去", "干", "处理", "打包",
    "整理", "跑", "执行", "查", "下载", "发送", "搞定", "安排", "生成",
)


def parse_dispatch(text: str, names) -> str | None:
    """从自然语言里识别"派活给某个外部智能体"。

    需同时命中（① 提到某个智能体名字 ② 含派活动词），否则视为普通聊天返回 None。
    例：「让 openclaw 把代码打包」→ "openclaw"；「openclaw 是什么」→ None。
    """
    text = text or ""
    hit = next((n for n in names if n and n in text), None)
    if not hit:
        return None
    if not any(v in text for v in DISPATCH_VERBS):
        return None
    return hit


class RemoteAgent:
    def __init__(self, name: str, endpoint: str, timeout: float = 30.0) -> None:
        self.name = name
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def available(self) -> bool:
        try:
            urllib.request.urlopen(self.endpoint + "/ping", timeout=1.5)
            return True
        except Exception:
            return False

    def dispatch(self, task: str, **params) -> dict:
        """把任务发过去并等结果回传。返回 {ok, result/error}。"""
        payload = json.dumps({"task": task, "params": params}).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint + "/task",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return {"ok": True, "agent": self.name, **data}
        except Exception as e:
            return {"ok": False, "agent": self.name, "error": str(e)}


class AgentHub:
    """管理多个外部智能体；按名字派活。"""

    def __init__(self, agents: dict | None = None) -> None:
        self.agents: dict[str, RemoteAgent] = {}
        for name, endpoint in (agents or {}).items():
            # 环境变量覆盖：DSOUL_AGENT_<名字大写>
            endpoint = os.environ.get(f"DSOUL_AGENT_{name.upper()}", endpoint)
            self.agents[name] = RemoteAgent(name, endpoint)

    def names(self) -> list[str]:
        return list(self.agents)

    def available(self) -> dict[str, bool]:
        return {n: a.available() for n, a in self.agents.items()}

    def dispatch(self, agent_name: str, task: str, **params) -> dict:
        agent = self.agents.get(agent_name)
        if agent is None:
            return {"ok": False, "error": f"未知智能体：{agent_name}（可用：{', '.join(self.agents) or '无'}）"}
        return agent.dispatch(task, **params)

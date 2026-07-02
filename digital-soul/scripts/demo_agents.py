#!/usr/bin/env python3
"""演示：机器人（大脑）隔空把活儿派给笔记本上的"爱马仕"和"openclaw"，再拿结果回传。

本地起两个 worker 线程模拟那两台机器，零依赖即可跑通整条链路。
用法：python scripts/demo_agents.py
"""

import pathlib
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))  # 便于 import agent_worker

from agent_worker import make_server  # noqa: E402
from dsoul.remote_agents import AgentHub  # noqa: E402


def main() -> None:
    servers = {
        "爱马仕": make_server("爱马仕", 9301),
        "openclaw": make_server("openclaw", 9302),
    }
    for s in servers.values():
        threading.Thread(target=s.serve_forever, daemon=True).start()
    time.sleep(0.3)

    hub = AgentHub({"爱马仕": "http://127.0.0.1:9301", "openclaw": "http://127.0.0.1:9302"})
    print("🛰️  在线智能体：", hub.available())
    print("—— 机器人隔空派活 ——")
    jobs = [
        ("openclaw", "add", {"a": 19, "b": 23}),
        ("爱马仕", "time", {}),
        ("openclaw", "echo", {"text": "帮我把这段整理成周报"}),
    ]
    for agent, task, kw in jobs:
        r = hub.dispatch(agent, task, **kw)
        status = r.get("result", r.get("error"))
        print(f"  派给「{agent}」干 [{task}] → 回传：{status}")

    for s in servers.values():
        s.shutdown()
    print("✅ 隔空控制 → 执行 → 返回消息，整条链路跑通。")


if __name__ == "__main__":
    main()

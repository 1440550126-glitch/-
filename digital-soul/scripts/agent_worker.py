#!/usr/bin/env python3
"""参考"外部智能体" worker：在你的笔记本 / 苹果主机上跑，接收数字分身派来的任务、
执行后把结果回传。监听 `POST /task` 与 `GET /ping`。

把 execute() 换成你真正的智能体（爱马仕 / openclaw / 任意自动化脚本）即可。

用法：
  python scripts/agent_worker.py --name openclaw --port 9302
"""

import argparse
import datetime
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def execute(name: str, task: str, params: dict) -> dict:
    """演示式任务处理。替换成你真正的智能体逻辑。"""
    if task == "echo":
        return {"result": params.get("text", "")}
    if task == "time":
        return {"result": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    if task == "add":
        return {"result": float(params.get("a", 0)) + float(params.get("b", 0))}
    return {"result": f"[{name}] 已（模拟）执行：{task}，参数={params}"}


def make_server(name: str, port: int, executor=execute) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code: int, obj: dict) -> None:
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/ping"):
                self._send(200, {"ok": True, "name": name})
            else:
                self._send(404, {"ok": False})

        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0") or 0)
            try:
                data = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                data = {}
            try:
                out = executor(name, data.get("task", ""), data.get("params", {}) or {})
                self._send(200, {"ok": True, **out})
            except Exception as e:
                self._send(200, {"ok": False, "error": str(e)})

    return ThreadingHTTPServer(("0.0.0.0", port), Handler)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="worker")
    ap.add_argument("--port", type=int, default=9301)
    args = ap.parse_args()
    srv = make_server(args.name, args.port)
    print(f"🛠 智能体 worker「{args.name}」监听 http://0.0.0.0:{args.port}（Ctrl+C 退出）", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()

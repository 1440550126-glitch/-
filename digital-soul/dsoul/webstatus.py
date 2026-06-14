"""极简 Web 状态页（Python 标准库，无第三方依赖）。

让你在手机/电脑浏览器里实时看分身现在"看到谁、记了什么、聊了啥"。
由 daemon.py --web 启动。
"""

from __future__ import annotations

import html
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _snapshot(agent, monitor) -> dict:
    present = sorted(monitor.present.keys()) if monitor is not None else []
    mems = [it["text"] for it in agent.memory.items[-8:]][::-1]
    journal = []
    if agent.journal is not None:
        journal = [
            f'{e.get("speaker", "?")}: {e.get("utterance", "")}'
            for e in agent.journal._all()[-8:]
        ][::-1]
    return {
        "name": agent.identity.get("name", "我"),
        "llm": bool(agent.llm.available),
        "memory_count": len(agent.memory.items),
        "present": present,
        "recent_memories": mems,
        "recent_journal": journal,
    }


def _page(s: dict) -> str:
    def ul(items):
        return "".join(f"<li>{html.escape(x)}</li>" for x in items) or "<li class=dim>—</li>"

    present = "、".join(html.escape(p) for p in s["present"]) or "暂时没看到人"
    on = "on" if s["llm"] else "off"
    llm_txt = "大模型已接入" if s["llm"] else "大模型降级"
    return f"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<meta http-equiv=refresh content=3>
<title>{html.escape(s['name'])} · 数字分身</title>
<style>
body{{font-family:-apple-system,system-ui,sans-serif;margin:0;background:#0f1115;color:#e6e6e6}}
.wrap{{max-width:640px;margin:0 auto;padding:18px}}
h1{{font-size:20px}}
.card{{background:#1a1d24;border-radius:12px;padding:14px 16px;margin:12px 0}}
.k{{color:#8aa0c0;font-size:13px;margin-bottom:6px}}
ul{{margin:0;padding-left:18px}} li{{margin:3px 0}}
.dim{{color:#666}}
.badge{{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px}}
.on{{background:#13402a;color:#5fdd9d}} .off{{background:#3a2a13;color:#e0b15f}}
</style></head>
<body><div class=wrap>
<h1>🧠 {html.escape(s['name'])} · 数字分身</h1>
<div class=card><span class="badge {on}">{llm_txt}</span>&nbsp;&nbsp;记忆 {s['memory_count']} 条</div>
<div class=card><div class=k>👁️ 现在看到谁</div><div>{present}</div></div>
<div class=card><div class=k>🧩 最近记住</div><ul>{ul(s['recent_memories'])}</ul></div>
<div class=card><div class=k>💬 最近对话</div><ul>{ul(s['recent_journal'])}</ul></div>
<p class=dim style="text-align:center">每 3 秒自动刷新 · /api/status 提供 JSON</p>
</div></body></html>"""


def start_web(agent, monitor=None, port: int = 8765):
    """在后台线程启动状态页，返回 server 对象。"""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # 静音访问日志
            pass

        def do_GET(self):
            snap = _snapshot(agent, monitor)
            if self.path.startswith("/api"):
                body = json.dumps(snap, ensure_ascii=False).encode("utf-8")
                ctype = "application/json; charset=utf-8"
            else:
                body = _page(snap).encode("utf-8")
                ctype = "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

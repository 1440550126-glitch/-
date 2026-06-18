"""本地 Web 图形界面：用标准库 http.server 提供聊天 UI 与 JSON API。

- 默认仅监听 127.0.0.1；--host 0.0.0.0 可供局域网团队共享（建议配 --token）。
- 单页应用内联（无任何外部 CDN），离线可用，手机/桌面浏览器自适应。
- 同一服务可被多人/多设备访问，即"团队共享记忆"的最简形态。
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

INDEX_HTML = """<!doctype html><html lang=zh><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Mnemo</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}
body{margin:0;font:15px/1.6 system-ui,-apple-system,"PingFang SC",sans-serif;
background:#0f1115;color:#e7e9ee;display:flex;height:100vh}
#side{width:280px;border-right:1px solid #232838;padding:16px;overflow:auto;background:#12141b}
#side h1{font-size:18px;margin:0 0 4px}#side .sub{color:#8b93a7;font-size:12px;margin-bottom:16px}
#side h2{font-size:12px;color:#8b93a7;text-transform:uppercase;margin:18px 0 6px}
#prof{white-space:pre-wrap;color:#c7cbd6;font-size:13px}
#main{flex:1;display:flex;flex-direction:column;min-width:0}
#log{flex:1;overflow:auto;padding:20px;display:flex;flex-direction:column;gap:14px}
.msg{max-width:760px;padding:10px 14px;border-radius:12px;white-space:pre-wrap;word-break:break-word}
.me{align-self:flex-end;background:#2b5cff;color:#fff}
.ai{align-self:flex-start;background:#1a1e29;border:1px solid #232838}
.sys{align-self:center;color:#8b93a7;font-size:12px}
#bar{display:flex;gap:8px;padding:14px;border-top:1px solid #232838;background:#12141b}
#inp{flex:1;background:#1a1e29;border:1px solid #2a3142;color:#e7e9ee;border-radius:10px;
padding:11px 14px;font:inherit;resize:none}#inp:focus{outline:1px solid #2b5cff}
#send{background:#2b5cff;color:#fff;border:0;border-radius:10px;padding:0 20px;font:inherit;cursor:pointer}
#send:disabled{opacity:.5}@media(max-width:680px){#side{display:none}}
</style></head><body>
<div id=side><h1>✦ Mnemo</h1><div class=sub id=meta>连接中…</div>
<div class=sub id=stat></div>
<h2>我对你的了解</h2><div id=prof>—</div></div>
<div id=main><div id=log></div>
<div id=bar><textarea id=inp rows=1 placeholder="跟 Mnemo 说点什么…（Enter 发送）"></textarea>
<button id=send>发送</button></div></div>
<script>
const tok=new URLSearchParams(location.search).get('token');
const api=p=>p+(tok?(p.includes('?')?'&':'?')+'token='+encodeURIComponent(tok):'');
const log=document.getElementById('log'),inp=document.getElementById('inp'),send=document.getElementById('send');
function add(t,cls){const d=document.createElement('div');d.className='msg '+cls;d.textContent=t;
log.appendChild(d);log.scrollTop=log.scrollHeight;return d}
async function refresh(){try{const r=await fetch(api('/api/profile'));const j=await r.json();
document.getElementById('prof').textContent=j.profile||'（还没积累到画像）';
const s=j.stats||{};document.getElementById('meta').dataset.s=JSON.stringify(s)}catch(e){}}
async function health(){try{const j=await (await fetch(api('/api/health'))).json();
document.getElementById('meta').textContent=j.provider+'/'+(j.model||'default')}catch(e){}}
async function stat(){try{const j=await (await fetch(api('/api/status'))).json();
const u=j.usage_today,r=j.reminders||0;let s=[];if(r)s.push('待办 '+r);
if(u&&u.calls)s.push('今日 '+u.calls+'次·'+(u.in_tok+u.out_tok)+'tok');
document.getElementById('stat').textContent=s.join('　·　')}catch(e){}}
async function go(){const m=inp.value.trim();if(!m)return;inp.value='';add(m,'me');
send.disabled=true;const t=add('思考中…','sys');
try{const r=await fetch(api('/api/chat'),{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({message:m,session:'web'})});const j=await r.json();
t.remove();add(j.reply||('[错误] '+(j.error||'未知')),'ai');refresh()}
catch(e){t.remove();add('[网络错误] '+e,'sys')}finally{send.disabled=false;inp.focus()}}
send.onclick=go;inp.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();go()}});
health();refresh();stat();setInterval(stat,30000);
add('你好，我是 Mnemo——你的本地 AI 伙伴，会记住你、越来越懂你。','ai');
</script></body></html>"""


def make_handler(app, lock, token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # 静默默认日志
            pass

        def _send(self, code, body, ctype="application/json"):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", f"{ctype}; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, ensure_ascii=False))

        def _auth(self):
            if not token:
                return True
            q = parse_qs(urlparse(self.path).query)
            given = (q.get("token", [None])[0] or self.headers.get("X-Mnemo-Token"))
            return given == token

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/":
                return self._send(200, INDEX_HTML, "text/html")
            if path == "/api/health":
                return self._json(200, {"ok": True, "provider": app.provider.name,
                                        "model": app.provider.model})
            if not self._auth():
                return self._json(401, {"error": "unauthorized"})
            if path == "/api/profile" and app.memory:
                return self._json(200, {"profile": app.memory.profile_summary(),
                                        "stats": app.memory.stats()})
            if path == "/api/facts" and app.memory:
                return self._json(200, {"facts": app.memory.all_facts(50)})
            if path == "/api/sessions" and app.memory:
                return self._json(200, {"sessions": app.memory.sessions()})
            if path == "/api/usage" and getattr(app, "usage", None):
                import time as _t
                return self._json(200, {"today": app.usage.summary(_t.time() - 86400),
                                        "total": app.usage.summary(),
                                        "by_model": app.usage.by_model()})
            if path == "/api/status":
                import time as _t
                out = {"provider": app.provider.name, "model": app.provider.model}
                if app.memory:
                    out["memory"] = app.memory.stats()
                    out["reminders"] = len(app.memory.pending_reminders())
                if getattr(app, "usage", None):
                    out["usage_today"] = app.usage.summary(_t.time() - 86400)
                return self._json(200, out)
            return self._json(404, {"error": "not found"})

        def do_POST(self):
            if not self._auth():
                return self._json(401, {"error": "unauthorized"})
            if urlparse(self.path).path != "/api/chat":
                return self._json(404, {"error": "not found"})
            length = int(self.headers.get("Content-Length") or 0)
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._json(400, {"error": "bad json"})
            msg = (payload.get("message") or "").strip()
            if not msg:
                return self._json(400, {"error": "empty"})
            session = payload.get("session") or "web"
            # Web 端无法交互确认：若用户开启了危险工具确认，则在此拒绝放行（auto_approve=False，
            # 且无 confirm 回调 → 危险工具被拦下），与终端一致地尊重该安全设置。
            cfg = getattr(app, "cfg", None)
            confirm_danger = bool(cfg and cfg.get("tools.confirm_danger", False))
            try:
                with lock:                      # 串行化，保护单连接 SQLite
                    reply = app.agent.run(msg, session=session, auto_approve=not confirm_danger)
            except Exception as e:  # noqa: BLE001
                return self._json(500, {"error": str(e)})
            return self._json(200, {"reply": reply})

    return Handler


def serve(app, host="127.0.0.1", port=8765, token=None):
    lock = threading.Lock()
    httpd = ThreadingHTTPServer((host, port), make_handler(app, lock, token))
    shown = host if host != "0.0.0.0" else "<本机IP>"
    url = f"http://{shown}:{port}/" + (f"?token={token}" if token else "")
    print(f"Mnemo Web 已启动：{url}")
    if host == "0.0.0.0":
        print("⚠ 正在对局域网开放（团队共享）。强烈建议设置 --token 防止未授权访问。")
    print("Ctrl-C 退出。")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.shutdown()
        print("\nWeb 服务已停止")

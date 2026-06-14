"""极简 Web 状态页 + 远程对话（Python 标准库，无第三方依赖）。

由 daemon.py --web 启动。手机/电脑浏览器即可：
- 实时看分身"看到谁 / 记了什么 / 聊了啥"
- 直接跟它聊天（可选择以谁的身份说话，对话同样走授权与人格）

⚠️ 它会暴露一个对话接口，请只在可信局域网使用。
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _owner(agent) -> str:
    for p in agent.authority.people.values():
        if p.get("trust") == "owner":
            return p["name"]
    return agent.identity.get("name", "我")


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
        "people": [p["name"] for p in agent.authority.people.values()],
        "owner": _owner(agent),
    }


PAGE = r"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>数字分身</title>
<style>
body{font-family:-apple-system,system-ui,sans-serif;margin:0;background:#0f1115;color:#e6e6e6}
.wrap{max-width:640px;margin:0 auto;padding:18px}
h1{font-size:20px}
.card{background:#1a1d24;border-radius:12px;padding:14px 16px;margin:12px 0}
.k{color:#8aa0c0;font-size:13px;margin-bottom:8px}
ul{margin:0;padding-left:18px} li{margin:3px 0}
.dim{color:#666}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px}
.on{background:#13402a;color:#5fdd9d} .off{background:#3a2a13;color:#e0b15f}
.row{display:flex;gap:8px;align-items:center;margin:8px 0}
select,input,button{font-size:15px;padding:8px;border-radius:8px;border:1px solid #2a2f3a;background:#0f1115;color:#e6e6e6}
input{flex:1} button{background:#2e7d32;border:none;color:#fff;padding:8px 14px}
.chat{max-height:240px;overflow:auto;display:flex;flex-direction:column;gap:6px;margin:8px 0}
.msg{padding:7px 11px;border-radius:12px;max-width:80%;white-space:pre-wrap;word-break:break-word}
.me{align-self:flex-end;background:#1565c0;color:#fff}
.soul{align-self:flex-start;background:#26303a}
</style></head>
<body><div class=wrap>
<h1 id=title>🧠 数字分身</h1>
<div class=card><span id=llm class="badge off">…</span>&nbsp;&nbsp;<span id=memc>记忆 …</span></div>
<div class=card><div class=k>👁️ 现在看到谁</div><div id=present>…</div></div>
<div class=card><div class=k>💬 跟 TA 聊聊</div>
  <div class=row><span class=dim>身份：</span><select id=speaker></select></div>
  <div id=chat class=chat></div>
  <form id=f class=row><input id=msg placeholder="说点什么…" autocomplete=off><button>发送</button></form>
</div>
<div class=card><div class=k>🧩 最近记住</div><ul id=mems></ul></div>
<div class=card><div class=k>🕘 最近对话</div><ul id=jour></ul></div>
<p class=dim style="text-align:center">状态每 3 秒自动刷新 · /api/status 提供 JSON</p>
</div>
<script>
const $=s=>document.querySelector(s);
let inited=false, soulName="它";
function esc(t){const d=document.createElement('div');d.textContent=t;return d.innerHTML;}
function li(a){return a.map(x=>'<li>'+esc(x)+'</li>').join('')||'<li class=dim>—</li>';}
async function refresh(){
  try{
    const s=await (await fetch('/api/status')).json();
    soulName=s.name;
    $('#title').textContent='🧠 '+s.name+' · 数字分身';
    $('#llm').textContent=s.llm?'大模型已接入':'大模型降级';
    $('#llm').className='badge '+(s.llm?'on':'off');
    $('#memc').textContent='记忆 '+s.memory_count+' 条';
    $('#present').textContent=s.present.length?s.present.join('、'):'暂时没看到人';
    $('#mems').innerHTML=li(s.recent_memories);
    $('#jour').innerHTML=li(s.recent_journal);
    if(!inited){$('#speaker').innerHTML=s.people.map(p=>'<option'+(p===s.owner?' selected':'')+'>'+esc(p)+'</option>').join('');inited=true;}
  }catch(e){}
}
function add(who,text,cls){const c=$('#chat');const d=document.createElement('div');d.className='msg '+cls;d.textContent=(who?who+'：':'')+text;c.appendChild(d);c.scrollTop=c.scrollHeight;}
$('#f').addEventListener('submit',async e=>{
  e.preventDefault();
  const t=$('#msg').value.trim(); if(!t)return;
  const sp=$('#speaker').value; add(sp,t,'me'); $('#msg').value='';
  try{
    const r=await (await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t,speaker:sp})})).json();
    add(soulName, r.reply, 'soul');
  }catch(e){ add(soulName,'（网络出错）','soul'); }
  refresh();
});
refresh(); setInterval(refresh,3000);
</script>
</body></html>"""


def start_web(agent, monitor=None, port: int = 8765):
    """在后台线程启动状态页 + 对话接口，返回 server 对象。"""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # 静音访问日志
            pass

        def _send(self, body: bytes, ctype: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/api/status"):
                body = json.dumps(_snapshot(agent, monitor), ensure_ascii=False).encode("utf-8")
                self._send(body, "application/json; charset=utf-8")
            else:
                self._send(PAGE.encode("utf-8"), "text/html; charset=utf-8")

        def do_POST(self):
            if not self.path.startswith("/api/chat"):
                self._send(b"{}", "application/json; charset=utf-8")
                return
            n = int(self.headers.get("Content-Length", "0") or 0)
            try:
                data = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                data = {}
            text = (data.get("text") or "").strip()
            speaker = (data.get("speaker") or _owner(agent)).strip()
            reply = agent.handle(speaker, text)["reply"] if text else ""
            body = json.dumps({"speaker": speaker, "reply": reply}, ensure_ascii=False).encode("utf-8")
            self._send(body, "application/json; charset=utf-8")

    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

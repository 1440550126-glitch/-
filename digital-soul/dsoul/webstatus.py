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
    journal, dispatches = [], []
    if agent.journal is not None:
        entries = agent.journal._all()
        journal = [
            f'{e.get("speaker", "?")}: {e.get("utterance", "")}'
            for e in entries[-8:]
        ][::-1]
        for e in entries[-16:]:
            ex = e.get("executed") or ""
            if isinstance(ex, str) and (ex.startswith("dispatch:") or ex.startswith("propose:")):
                kind, who = ex.split(":", 1)
                tag = "✅ 已派活" if kind == "dispatch" else "💡 提议"
                dispatches.append(f'{tag} → {who}：{e.get("utterance", "")}')
        dispatches = dispatches[::-1][:6]
    mood_char, mood_levels = None, {}
    if getattr(agent, "emotions", None):
        mood_levels = agent.emotions.snapshot()
        mood_char = max(mood_levels, key=mood_levels.get) if mood_levels else None
    tasks_open, tasks_done = [], 0
    if getattr(agent, "tasks", None) is not None:
        tasks_open = [
            f'{t["agent"]}：{t["instruction"]}（试 {t["attempts"]} 次）'
            for t in agent.tasks.open()
        ][::-1][:6]
        tasks_done = len(agent.tasks.done())
    reflections = agent.recent_reflections() if hasattr(agent, "recent_reflections") else []
    graph_top, graph_viz = [], {"nodes": [], "edges": []}
    if hasattr(agent, "memory_graph"):
        try:
            g = agent.memory_graph()
            graph_top = [n for n, _ in g.central(6)]
            deg = {n: sum(w.values()) for n, w in g.adj.items()}
            top = [n for n, _ in sorted(deg.items(), key=lambda x: -x[1])[:12]]
            idx = set(top)
            when_of = {it["text"]: int(it["when"]) for it in agent.memory.items
                       if str(it.get("when") or "").isdigit()}

            def _nyear(n):
                ys = [when_of[t] for t in g.mem.get(n, []) if t in when_of]
                return min(ys) if ys else None

            graph_viz["nodes"] = [
                {"id": n, "label": n, "kind": g.meta.get(n, {}).get("kind", "topic"),
                 "deg": deg[n], "year": _nyear(n)}
                for n in top]
            seen = set()
            for a in top:
                for b, w in g.adj.get(a, {}).items():
                    if b in idx and (b, a) not in seen:
                        seen.add((a, b))
                        graph_viz["edges"].append({"a": a, "b": b, "w": w})
        except Exception:
            pass
    people_names = [p["name"] for p in agent.authority.people.values() if p.get("name")]
    timeline = []
    try:
        for it in agent.memory.timeline():
            w = it.get("when")
            if w and str(w).isdigit():
                text = it["text"]
                timeline.append({"year": str(w), "text": text,
                                 "people": [n for n in people_names if n and n in text]})
    except Exception:
        timeline = []
    timeline = timeline[:40]
    tl_entities = sorted({p for e in timeline for p in e["people"]})
    fading = []
    if hasattr(agent, "fading_memories"):
        try:
            fading = [f"{t}（{int(s * 100)}%）" for s, t in agent.fading_memories(5)]
        except Exception:
            fading = []
    dreams = []
    if getattr(agent, "dreams", None) is not None:
        try:
            dreams = [{"text": r["text"], "mood": r.get("mood")} for r in agent.dreams.recent(3)]
        except Exception:
            dreams = []
    selfnar, selfhist = "", []
    if hasattr(agent, "self_narrative"):
        try:
            selfnar = agent.self_narrative()
        except Exception:
            selfnar = ""
    if getattr(agent, "selflog", None) is not None:
        try:
            selfhist = [f'{r["date"]}：{r["text"].split("。")[0]}' for r in agent.selflog.recent(5)]
        except Exception:
            selfhist = []
    values = list(agent.values) if getattr(agent, "values", None) else []
    devices = agent.devices.rows() if getattr(agent, "devices", None) is not None else []
    scenes = agent.scenes.names() if getattr(agent, "scenes", None) is not None else []
    triggers = [t["desc"] for t in agent.triggers.all()] if getattr(agent, "triggers", None) is not None else []
    plan_items = []
    if getattr(agent, "plan", None) is not None:
        plan_items = [
            ("✅ " if it["status"] == "done" else "▢ ") + it.get("text", "")
            for it in agent.plan.items
        ][:6]
    return {
        "name": agent.identity.get("name", "我"),
        "llm": bool(agent.llm.available),
        "memory_count": len(agent.memory.items),
        "present": present,
        "recent_memories": mems,
        "recent_journal": journal,
        "dispatches": dispatches,
        "tasks_open": tasks_open,
        "tasks_done": tasks_done,
        "reflections": reflections,
        "graph": graph_top,
        "graph_viz": graph_viz,
        "timeline": timeline,
        "timeline_entities": tl_entities,
        "fading": fading,
        "dreams": dreams,
        "self": selfnar,
        "self_history": selfhist,
        "values": values,
        "plan": plan_items,
        "devices": devices,
        "scenes": scenes,
        "triggers": triggers,
        "mood": mood_char,
        "mood_levels": mood_levels,
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
.barrow{display:flex;align-items:center;gap:8px;margin:4px 0}
.barlab{width:24px;font-size:15px;text-align:center}
.bartrk{flex:1;height:8px;background:#0f1115;border-radius:6px;overflow:hidden}
.bartrk i{display:block;height:100%;background:linear-gradient(90deg,#2e7d32,#5fdd9d)}
.devrow{display:flex;align-items:center;gap:8px;margin:5px 0}
.devname{width:46px} .devst{flex:1;color:#8aa0c0;font-size:13px}
.devbtn{padding:3px 12px;font-size:13px;background:#2a2f3a;border:1px solid #3a4150;color:#e6e6e6;border-radius:8px}
.tlyear{color:#5fdd9d;font-weight:600;margin:8px 0 2px;border-left:3px solid #2e7d32;padding-left:8px}
.tlitem{color:#cbd5e1;font-size:13px;margin:2px 0 2px 16px;position:relative}
.tlitem:before{content:"•";color:#2e7d32;position:absolute;left:-10px}
</style></head>
<body><div class=wrap>
<h1 id=title>🧠 数字分身</h1>
<div class=card><span id=llm class="badge off">…</span>&nbsp;&nbsp;<span id=memc>记忆 …</span></div>
<div class=card><div class=k>👁️ 现在看到谁</div><div id=present>…</div></div>
<div class=card><div class=k>🏠 设备</div><div id=devices></div></div>
<div class=card><div class=k>🎬 场景</div><div id=scenes></div></div>
<div class=card><div class=k>⏰ 自动化</div><ul id=triggers></ul>
  <form id=trigf class=row style="margin:6px 0"><input id=triginput placeholder="如：每天22点提醒锁门" autocomplete=off><button>添加</button></form>
  <button id=clrtrig class=devbtn>清空</button></div>
<div class=card><div class=k>💞 此刻心情</div><div id=mood>…</div><div id=moodbars></div></div>
<div class=card><div class=k>🪞 此刻的我</div><div id=selfnar style="font-size:14px;line-height:1.6">…</div>
  <div class=k style="margin-top:10px">💎 我珍视的</div><div id=values class=dim></div>
  <div class=k style="margin-top:10px">📈 成长史</div><ul id=selfhist></ul></div>
<div class=card><div class=k>🤵 管家</div>
  <button id=brief>☀️ 要一份简报</button>&nbsp;<button id=diag style="background:#37474f">🩺 系统自检</button></div>
<div class=card><div class=k>💬 跟 TA 聊聊</div>
  <div class=row><span class=dim>身份：</span><select id=speaker></select></div>
  <div id=chat class=chat></div>
  <form id=f class=row><input id=msg placeholder="说点什么…" autocomplete=off><button>发送</button></form>
</div>
<div class=card><div class=k>🗓️ 今天的计划</div><ul id=plan></ul></div>
<div class=card><div class=k>💡 它最近的领悟</div><ul id=refl></ul></div>
<div class=card><div class=k>🧠 正在淡忘</div><ul id=fading></ul></div>
<div class=card><div class=k>🌙 昨夜的梦</div><div id=dreams></div></div>
<div class=card><div class=k>🕸️ 关系图谱</div><div id=graph></div>
  <div class=row style="margin-top:6px"><button id=gplay class=devbtn>▶ 生长</button><input id=gyslider type=range style="flex:1"><span id=gylabel class=dim>全部</span></div>
  <div id=graphtop class=dim></div></div>
<div class=card><div class=k>📜 一生时间线</div><div id=tlfilters></div><div id=timeline></div></div>
<div class=card><div class=k>🧩 最近记住</div><ul id=mems></ul></div>
<div class=card><div class=k>🕘 最近对话</div><ul id=jour></ul></div>
<div class=card><div class=k>🛰️ 最近派活 / 提议</div><ul id=disp></ul></div>
<div class=card><div class=k>📋 待办看板 <span id=taskstat class=dim></span></div><ul id=tasks></ul>
  <button id=retry style="display:none;margin-top:8px;background:#5a3a13">↻ 重试全部待办</button></div>
<p class=dim style="text-align:center">状态每 3 秒自动刷新 · /api/status 提供 JSON</p>
</div>
<script>
const $=s=>document.querySelector(s);
const MOODS={"喜":"😄 愉悦","怒":"😠 生气","哀":"😢 低落","惧":"😨 不安","爱":"❤️ 满心欢喜","恶":"😒 有点反感","欲":"🥺 渴望陪伴"};
const EMO={"喜":"😄","怒":"😠","哀":"😢","惧":"😨","爱":"❤️","恶":"😒","欲":"🥺"};
const SEVEN=["喜","怒","哀","惧","爱","恶","欲"];
function bars(lv){return SEVEN.map(e=>{const v=Math.max(0,Math.min(100,Math.round((lv[e]||0)*100)));return '<div class=barrow><span class=barlab title="'+e+'">'+EMO[e]+'</span><span class=bartrk><i style="width:'+v+'%"></i></span></div>';}).join('');}
function radar(lv){const S=160,c=S/2,R=54,n=SEVEN.length;function pt(i,r){const a=-Math.PI/2+2*Math.PI*i/n;return [c+r*Math.cos(a),c+r*Math.sin(a)];}let s='<svg width="170" height="160" viewBox="0 0 '+S+' '+S+'">';[0.5,1].forEach(g=>{const pts=SEVEN.map((_,i)=>pt(i,R*g).map(v=>v.toFixed(1)).join(',')).join(' ');s+='<polygon points="'+pts+'" fill="none" stroke="#2a2f3a"/>';});SEVEN.forEach((e,i)=>{const[ax,ay]=pt(i,R);s+='<line x1='+c+' y1='+c+' x2='+ax.toFixed(1)+' y2='+ay.toFixed(1)+' stroke="#2a2f3a"/>';const[lx,ly]=pt(i,R+11);s+='<text x='+lx.toFixed(1)+' y='+ly.toFixed(1)+' font-size="11" text-anchor="middle" dominant-baseline="middle">'+EMO[e]+'</text>';});const vp=SEVEN.map((e,i)=>pt(i,R*Math.max(0,Math.min(1,lv[e]||0))).map(v=>v.toFixed(1)).join(',')).join(' ');s+='<polygon points="'+vp+'" fill="#5fdd9d" fill-opacity="0.35" stroke="#5fdd9d"/>';return s+'</svg>';}
function devRow(d){const st=d.on?('开'+(d.detail?(' '+d.detail):'')):'关';return '<div class=devrow><span class=devname>'+d.label+'</span><span class=devst>'+st+'</span><button class=devbtn onclick="dev(\''+d.key+'\',\'on\')">开</button><button class=devbtn onclick="dev(\''+d.key+'\',\'off\')">关</button></div>';}
async function dev(k,a){const sp=$('#speaker').value;try{const r=await (await fetch('/api/device',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device:k,action:a,speaker:sp})})).json();add(soulName,r.reply,'soul');}catch(e){}refresh();}
async function scene(n){const sp=$('#speaker').value;try{const r=await (await fetch('/api/scene',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scene:n,speaker:sp})})).json();add(soulName,r.reply,'soul');}catch(e){}refresh();}
let inited=false, soulName="它";
function esc(t){const d=document.createElement('div');d.textContent=t;return d.innerHTML;}
function renderTimeline(tl){if(!tl||!tl.length)return '<span class=dim>暂无带年份的记忆</span>';let h='',last=null;tl.forEach(e=>{if(e.year!==last){h+='<div class=tlyear>'+esc(e.year)+'</div>';last=e.year;}h+='<div class=tlitem>'+esc(e.text)+'</div>';});return h;}
const MCOL={"喜":"#e0b15f","怒":"#c0504d","哀":"#4a6fa5","惧":"#6a5a8a","爱":"#c05a7d","恶":"#5a7a5a","欲":"#7d6a4a"};
function hashStr(t){let h=0;for(let i=0;i<t.length;i++)h=(h*31+t.charCodeAt(i))&0x7fffffff;return h||1;}
function dreamArt(d){const col=MCOL[d.mood]||'#566';let h=hashStr(d.text||'');const W=300,H=64;let s='<svg width="100%" height="64" viewBox="0 0 '+W+' '+H+'" style="border-radius:8px;background:#0f1115">';for(let i=0;i<7;i++){h=(h*1103515245+12345)&0x7fffffff;const x=h%W,y=(h>>7)%H,r=8+(h>>15)%24;s+='<circle cx='+x+' cy='+y+' r='+r+' fill="'+col+'" fill-opacity="0.16"/>';}return s+'</svg>';}
function renderDreams(ds){if(!ds||!ds.length)return '<div class=dim>还没做过梦（睡一觉 / sleep 后生成）</div>';return ds.map(d=>'<div style="margin:8px 0">'+dreamArt(d)+'<div class=dim style="font-size:13px;font-style:italic;margin-top:4px">'+esc(d.text)+'</div></div>').join('');}
let tlFilter=null, _tl=[];
function setTL(e){tlFilter=e||null;gHi=tlFilter;drawTL();drawGraph();}
function drawTL(){let tl=_tl;if(tlFilter)tl=tl.filter(x=>(x.people&&x.people.includes(tlFilter))||(x.text&&x.text.indexOf(tlFilter)>=0));$('#timeline').innerHTML=renderTimeline(tl);}
function renderTLfilters(ents){let h='<button class=devbtn style="margin:2px" onclick="setTL(\'\')">全部</button>';(ents||[]).forEach(e=>h+='<button class=devbtn style="margin:2px" onclick="setTL(\''+e+'\')">'+esc(e)+'</button>');return h;}
function renderGraph(gv,maxYear,hi){if(!gv||!gv.nodes||!gv.nodes.length)return '';let nodes=gv.nodes;if(maxYear)nodes=nodes.filter(n=>!n.year||n.year<=maxYear);if(!nodes.length)return '';const ids=new Set(nodes.map(n=>n.id));const edges=(gv.edges||[]).filter(e=>ids.has(e.a)&&ids.has(e.b));const nbr=new Set();if(hi){edges.forEach(e=>{if(e.a===hi)nbr.add(e.b);if(e.b===hi)nbr.add(e.a);});}const W=320,H=290,cx=W/2,cy=H/2,R=108;const center=nodes.reduce((a,b)=>b.deg>a.deg?b:a,nodes[0]);const others=nodes.filter(x=>x!==center);const pos={};pos[center.id]={x:cx,y:cy};others.forEach((nd,i)=>{const ang=2*Math.PI*i/others.length;pos[nd.id]={x:cx+R*Math.cos(ang),y:cy+R*Math.sin(ang)};});let s='<svg width="100%" viewBox="0 0 '+W+' '+H+'">';edges.forEach(e=>{const p=pos[e.a],q=pos[e.b];if(!p||!q)return;const on=hi&&(e.a===hi||e.b===hi);const col=on?'#5fdd9d':'#2e7d32';const op=hi?(on?0.95:0.12):0.5;const wd=on?Math.min(5,e.w+1.5):Math.min(4,e.w);s+='<line x1='+p.x.toFixed(1)+' y1='+p.y.toFixed(1)+' x2='+q.x.toFixed(1)+' y2='+q.y.toFixed(1)+' stroke="'+col+'" stroke-opacity="'+op+'" stroke-width="'+wd+'"'+(on?' stroke-dasharray="2 2"':'')+'/>';});nodes.forEach(nd=>{const p=pos[nd.id],r=nd.kind==='person'?8:5,col=nd.kind==='person'?'#1565c0':'#5a3a13';const dim=hi&&nd.id!==hi&&!nbr.has(nd.id);s+='<g style="cursor:pointer" opacity="'+(dim?0.28:1)+'" onclick="setTL(\''+nd.id+'\')">';s+='<circle cx='+p.x.toFixed(1)+' cy='+p.y.toFixed(1)+' r='+(nd.id===hi?r+2:r)+' fill="'+col+'"/>';s+='<text x='+p.x.toFixed(1)+' y='+(p.y-r-3).toFixed(1)+' font-size="11" fill="#cbd5e1" text-anchor="middle">'+esc(nd.label)+'</text>';s+='</g>';});return s+'</svg>';}
let _gv={nodes:[],edges:[]},gYear=null,gHi=null,_play=null;
function gYears(gv){const ys=(gv.nodes||[]).map(n=>n.year).filter(y=>y);return ys.length?[Math.min.apply(0,ys),Math.max.apply(0,ys)]:null;}
function drawGraph(){$('#graph').innerHTML=renderGraph(_gv,gYear,gHi)||'<span class=dim>记忆还太少，画不出关系网</span>';}
function setGY(v){gYear=v?parseInt(v):null;$('#gylabel').textContent=gYear?('截至 '+gYear):'全部';drawGraph();}
function playGraph(){const r=gYears(_gv);if(!r){return;}if(_play){clearInterval(_play);_play=null;return;}let y=r[0];const sl=$('#gyslider');_play=setInterval(()=>{setGY(y);if(sl)sl.value=y;if(y>=r[1]){clearInterval(_play);_play=null;}y++;},800);}
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
    $('#devices').innerHTML=(s.devices&&s.devices.length)?s.devices.map(devRow).join(''):'<span class=dim>无设备</span>';
    $('#scenes').innerHTML=(s.scenes&&s.scenes.length)?s.scenes.map(n=>'<button class=devbtn style="margin:3px" onclick="scene(\''+n+'\')">'+n+'</button>').join(''):'<span class=dim>无</span>';
    $('#triggers').innerHTML=li(s.triggers||[]);
    $('#selfnar').textContent=s.self||'…';
    $('#selfhist').innerHTML=(s.self_history&&s.self_history.length)?li(s.self_history):'<li class=dim>还没攒下成长史（每天记一版）</li>';
    $('#values').textContent=(s.values&&s.values.length)?s.values.join(' › '):'';
    $('#mood').textContent=s.mood?(MOODS[s.mood]||s.mood):'平静';
    $('#moodbars').innerHTML=s.mood_levels?radar(s.mood_levels):'';
    $('#disp').innerHTML=li(s.dispatches||[]);
    const op=s.tasks_open||[];
    $('#taskstat').textContent='· 欠 '+op.length+' 件 · 已办成 '+(s.tasks_done||0)+' 件';
    $('#tasks').innerHTML=op.length?li(op):'<li class=dim>都办妥啦 🎉</li>';
    $('#retry').style.display=op.length?'inline-block':'none';
    $('#plan').innerHTML=li(s.plan||[]);
    $('#refl').innerHTML=li(s.reflections||[]);
    $('#fading').innerHTML=(s.fading&&s.fading.length)?li(s.fading):'<li class=dim>记忆都还清晰</li>';
    $('#dreams').innerHTML=renderDreams(s.dreams);
    _gv=s.graph_viz||{nodes:[],edges:[]};const _yr=gYears(_gv),_sl=$('#gyslider');if(_yr){_sl.min=_yr[0];_sl.max=_yr[1];if(_sl.dataset.init!=='1'){_sl.value=_yr[1];_sl.dataset.init='1';}}drawGraph();
    $('#graphtop').textContent=((s.graph&&s.graph.length)?('最核心：'+s.graph.join(' · ')):'')+((s.graph_viz&&s.graph_viz.nodes.length)?'　·　点节点筛选时间线 / ▶生长看关系网长出来':'');
    _tl=s.timeline||[]; $('#tlfilters').innerHTML=renderTLfilters(s.timeline_entities); drawTL();
    $('#mems').innerHTML=li(s.recent_memories);
    $('#jour').innerHTML=li(s.recent_journal);
    if(!inited){$('#speaker').innerHTML=s.people.map(p=>'<option'+(p===s.owner?' selected':'')+'>'+esc(p)+'</option>').join('');inited=true;}
  }catch(e){}
}
function add(who,text,cls){const c=$('#chat');const d=document.createElement('div');d.className='msg '+cls;d.textContent=(who?who+'：':'')+text;c.appendChild(d);c.scrollTop=c.scrollHeight;}
async function ask(t){
  t=(t||'').trim(); if(!t)return;
  const sp=$('#speaker').value; add(sp,t,'me');
  try{
    const r=await (await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t,speaker:sp})})).json();
    add(soulName, r.reply, 'soul');
    if(r.associations&&r.associations.length){const c=$('#chat');const d=document.createElement('div');d.className='msg soul';d.style.opacity='0.7';d.style.fontSize='12px';d.textContent='💭 这让我想起：'+r.associations.join('；');c.appendChild(d);c.scrollTop=c.scrollHeight;}
  }catch(e){ add(soulName,'（网络出错）','soul'); }
  refresh();
}
$('#f').addEventListener('submit',e=>{e.preventDefault();const t=$('#msg').value;$('#msg').value='';ask(t);});
$('#brief').addEventListener('click',()=>ask('简报'));
$('#diag').addEventListener('click',()=>ask('系统自检'));
$('#clrtrig').addEventListener('click',()=>ask('清空所有自动化'));
$('#trigf').addEventListener('submit',e=>{e.preventDefault();const t=$('#triginput').value;$('#triginput').value='';ask(t);});
$('#gplay').addEventListener('click',playGraph);
$('#gyslider').addEventListener('input',e=>setGY(e.target.value));
$('#retry').addEventListener('click',async()=>{
  const sp=$('#speaker').value; const b=$('#retry'); b.disabled=true;
  try{
    const r=await (await fetch('/api/retry',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({speaker:sp})})).json();
    add(soulName, r.reply||'（已重试）','soul');
  }catch(e){ add(soulName,'（网络出错）','soul'); }
  b.disabled=false; refresh();
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
            n = int(self.headers.get("Content-Length", "0") or 0)
            try:
                data = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                data = {}
            speaker = (data.get("speaker") or _owner(agent)).strip()
            if self.path.startswith("/api/device"):
                res = agent.device_control(speaker, data.get("device"), data.get("action"), data.get("value")) \
                    if hasattr(agent, "device_control") else {"msg": "暂不支持"}
                rows = agent.devices.rows() if getattr(agent, "devices", None) else []
                body = json.dumps({"reply": res.get("msg", ""), "devices": rows}, ensure_ascii=False).encode("utf-8")
                self._send(body, "application/json; charset=utf-8")
                return
            if self.path.startswith("/api/scene"):
                res = agent.run_scene(speaker, data.get("scene")) if hasattr(agent, "run_scene") else {"msg": "暂不支持"}
                rows = agent.devices.rows() if getattr(agent, "devices", None) else []
                body = json.dumps({"reply": res.get("msg", ""), "devices": rows}, ensure_ascii=False).encode("utf-8")
                self._send(body, "application/json; charset=utf-8")
                return
            if self.path.startswith("/api/retry"):
                res = agent.retry_open(speaker) if hasattr(agent, "retry_open") else {"reply": "暂不支持重试"}
                body = json.dumps({"speaker": speaker, "reply": res.get("reply", "")}, ensure_ascii=False).encode("utf-8")
                self._send(body, "application/json; charset=utf-8")
                return
            if self.path.startswith("/api/chat"):
                text = (data.get("text") or "").strip()
                res = agent.handle(speaker, text) if text else {"reply": "", "associations": []}
                body = json.dumps({"speaker": speaker, "reply": res.get("reply", ""),
                                   "associations": res.get("associations", [])},
                                  ensure_ascii=False).encode("utf-8")
                self._send(body, "application/json; charset=utf-8")
                return
            self._send(b"{}", "application/json; charset=utf-8")

    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

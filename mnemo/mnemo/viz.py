"""把记忆图谱渲染成一个自包含 HTML（内联力导向布局，无任何外部依赖）。"""
from __future__ import annotations

import json

_TEMPLATE = """<!doctype html><html lang=zh><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>html,body{margin:0;height:100%;background:#0f1115;color:#e7e9ee;
font:13px system-ui,"PingFang SC",sans-serif;overflow:hidden}
#h{position:fixed;top:12px;left:16px;z-index:2}#h b{font-size:16px}
#h span{color:#8b93a7}canvas{display:block}</style></head><body>
<div id=h><b>✦ __TITLE__</b> &nbsp;<span id=meta></span></div>
<canvas id=c></canvas><script>
const DATA=__DATA__;
const c=document.getElementById('c'),x=c.getContext('2d');
let W,H;function size(){W=c.width=innerWidth;H=c.height=innerHeight}size();onresize=size;
document.getElementById('meta').textContent=DATA.nodes.length+' 条记忆 · '+DATA.edges.length+' 条关联';
const COL={identity:'#ffb454',preference:'#7ee787',fact:'#6cb6ff',reminder:'#ff7b72'};
const N=DATA.nodes.map(n=>({...n,x:W/2+(Math.random()-.5)*300,y:H/2+(Math.random()-.5)*300,vx:0,vy:0}));
const idx={};N.forEach((n,i)=>idx[n.id]=i);
const E=DATA.edges.map(e=>({s:idx[e.source],t:idx[e.target],w:e.w}));
let ticks=0;
function step(){
 for(let i=0;i<N.length;i++)for(let j=i+1;j<N.length;j++){
  let a=N[i],b=N[j],dx=a.x-b.x,dy=a.y-b.y,d=Math.hypot(dx,dy)||1,f=2200/(d*d);
  a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f;}
 for(const e of E){let a=N[e.s],b=N[e.t],dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1,
  f=(d-90)*0.01*Math.min(e.w,4);a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f;}
 for(const n of N){n.vx+=(W/2-n.x)*0.002;n.vy+=(H/2-n.y)*0.002;
  n.x+=(n.vx*=0.85);n.y+=(n.vy*=0.85);}
}
function draw(){
 x.clearRect(0,0,W,H);x.strokeStyle='rgba(120,140,180,.18)';
 for(const e of E){x.beginPath();x.moveTo(N[e.s].x,N[e.s].y);x.lineTo(N[e.t].x,N[e.t].y);x.stroke();}
 for(const n of N){let r=5+(n.importance||1)*1.6;x.beginPath();x.arc(n.x,n.y,r,0,7);
  x.fillStyle=COL[n.kind]||'#6cb6ff';x.fill();
  x.fillStyle='#c7cbd6';x.font='11px system-ui';x.fillText(n.text,n.x+r+3,n.y+3);}
}
function loop(){if(ticks++<400)step();draw();requestAnimationFrame(loop);}loop();
let drag=null;c.onmousedown=e=>{for(const n of N)if(Math.hypot(n.x-e.clientX,n.y-e.clientY)<12){drag=n;break}};
onmousemove=e=>{if(drag){drag.x=e.clientX;drag.y=e.clientY;drag.vx=drag.vy=0;ticks=Math.min(ticks,200)}};
onmouseup=()=>drag=null;
</script></body></html>"""


def render_graph_html(data: dict, title: str = "Mnemo 记忆图谱") -> str:
    return (_TEMPLATE
            .replace("__TITLE__", title)
            .replace("__DATA__", json.dumps(data, ensure_ascii=False)))

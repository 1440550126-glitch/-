// 控制面板前端页面（内联，零外链）。由 panel.js 提供。
export const PAGE = `<!doctype html>
<html lang="zh"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>SUNO 批量挂机 · 控制台</title>
<style>
:root{--bg:#0e0f13;--card:#181a21;--line:#262a35;--fg:#e7e9ee;--mut:#8a90a2;--acc:#7c5cff;--ok:#2ecc71;--warn:#ffb020;--err:#ff5470}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,"PingFang SC","Microsoft YaHei",system-ui,sans-serif}
.wrap{max-width:900px;margin:0 auto;padding:24px}
h1{font-size:18px;margin:0 0 4px}.sub{color:var(--mut);font-size:12px;margin-bottom:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:16px}
.bar{height:10px;background:#22252f;border-radius:6px;overflow:hidden;margin:10px 0}
.bar>i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--acc),#a98bff);transition:width .4s}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.big{font-size:22px;font-weight:600}.mut{color:var(--mut)}
button{border:0;border-radius:10px;padding:10px 18px;font-size:14px;font-weight:600;cursor:pointer;color:#fff;background:#2a2e3a;transition:.15s}
button:hover{filter:brightness(1.15)}button:active{transform:translateY(1px)}
.b-pause{background:var(--warn);color:#1a1200}.b-resume{background:var(--ok);color:#04210f}.b-skip{background:#3a3f4d}.b-stop{background:var(--err)}
.pill{font-size:12px;padding:3px 10px;border-radius:20px;background:#22252f;color:var(--mut)}
.pill.run{background:rgba(124,92,255,.18);color:#b7a6ff}.pill.pause{background:rgba(255,176,32,.18);color:var(--warn)}.pill.done{background:rgba(46,204,113,.18);color:var(--ok)}
#cur{font-size:16px;font-weight:600;margin-top:6px}#style{color:var(--mut);font-size:13px}
#log{height:320px;overflow:auto;font:12px/1.6 ui-monospace,Menlo,Consolas,monospace;background:#0b0c10;border:1px solid var(--line);border-radius:10px;padding:12px}
.l-ok{color:var(--ok)}.l-err{color:var(--err)}.l-warn{color:var(--warn)}.l-dl{color:#5ac8fa}.l-mut{color:var(--mut)}
.wait{color:var(--acc);font-weight:600}
</style></head>
<body><div class="wrap">
<h1>🎛 SUNO 批量挂机 · 控制台</h1>
<div class="sub">本地控制，不上传任何数据。关闭页面不影响挂机；重开此页即可重新连上。</div>

<div class="card">
  <div class="row" style="justify-content:space-between">
    <div><span class="big" id="done">0</span> <span class="mut">/ <span id="total">0</span> 首</span></div>
    <span class="pill" id="phase">空闲</span>
  </div>
  <div class="bar"><i id="fill"></i></div>
  <div id="cur" class="mut">等待开始…</div>
  <div id="style"></div>
  <div id="wait" class="wait" style="margin-top:8px"></div>
</div>

<div class="card row">
  <button class="b-pause" onclick="cmd('pause')">⏸ 暂停</button>
  <button class="b-resume" onclick="cmd('resume')">▶ 继续</button>
  <button class="b-skip" onclick="cmd('skip')">⤼ 跳过等待</button>
  <button class="b-stop" onclick="cmd('stop')">⏹ 停止</button>
</div>

<div class="card">
  <div class="mut" style="margin-bottom:8px">实时日志</div>
  <div id="log"></div>
</div>
</div>
<script>
const $=id=>document.getElementById(id);
function cmd(c){fetch('/cmd/'+c,{method:'POST'});}
function line(cls,txt){const l=$('log');const d=document.createElement('div');if(cls)d.className=cls;
  d.textContent='['+new Date().toLocaleTimeString('zh-CN',{hour12:false})+'] '+txt;
  l.appendChild(d);l.scrollTop=l.scrollHeight;}
function setPhase(p){const el=$('phase');const m={running:['运行中','run'],paused:['已暂停','pause'],done:['已完成','done'],idle:['空闲','']};
  const[t,c]=m[p]||[p,''];el.textContent=t;el.className='pill '+c;}
function prog(done,total){$('done').textContent=done;$('total').textContent=total;$('fill').style.width=total?(done/total*100)+'%':'0';}
let total=0,done=0;
const es=new EventSource('/events');
es.onmessage=e=>{const{event,data}=JSON.parse(e.data);
 if(event==='snapshot'){total=data.total;done=data.done;prog(done,total);setPhase(data.phase);return;}
 if(event==='start'){total=data.total;done=0;prog(0,total);setPhase('running');line('l-mut','开始，共 '+total+' 首'+(data.dryRun?'（dry-run）':''));return;}
 if(event==='wait'){$('wait').textContent=data.left>0?('⏳ '+data.label+'：'+data.left+'s'):'';return;}
 if(event==='song'){
   const tag='['+data.i+'/'+data.total+'] ';
   if(data.phase==='generating')line('l-mut',tag+'✍️ 生成内容：'+(data.theme||''));
   else if(data.phase==='filling'){$('cur').textContent='🎵 '+(data.title||'(无题)');$('cur').className='';$('style').textContent=(data.style||'')+(data.playlist?(' · 🗂 '+data.playlist):'')+(data.instrumental?' · 器乐':'');
     if(data.warnings&&data.warnings.length)line('l-warn',tag+'⚠ '+data.warnings.join('；'));}
   else if(data.phase==='retry')line('l-warn',tag+'↻ 第 '+data.attempt+'/'+data.max+' 次重试：'+(data.message||''));
   else if(data.phase==='submitted'){done++;prog(done,total);line('l-ok',tag+'✅ 已提交：'+(data.title||'')+(data.playlist?(' → '+data.playlist):'')+(data.credits?(' · '+data.credits):''));}
   else if(data.phase==='dry'){done++;prog(done,total);line('l-mut',tag+'✓ 已填表（dry-run）');}
   else if(data.phase==='credits'){line('l-err',tag+'🛑 额度不足，已暂停：'+(data.message||'')+'（充值后点“继续”）');setPhase('paused');}
   else if(data.phase==='error')line('l-err',tag+'❌ '+(data.message||'失败'));
   return;}
 if(event==='download')line('l-dl','📥 已下载：'+(data.title||data.id));
 if(event==='harvest-done')line('l-dl','📥 下载收尾，共 '+data.total+' 个音频');
 if(event==='playlist')line(data.ok?'l-ok':'l-warn','🗂 '+(data.ok?('已加入「'+data.playlist+'」：'):'未能归类：')+(data.title||''));
 if(event==='playlist-done')line('l-mut','🗂 歌单归类：成功 '+data.ok+' · 未成 '+data.miss);
 if(event==='log')line('l-mut',data.message);
 if(event==='done'){setPhase('done');line('l-ok','全部结束：成功 '+data.ok+' · 失败/未确认 '+data.fail);$('wait').textContent='';}
};
es.onerror=()=>line('l-mut','（连接中断，正在重连…）');
</script>
</body></html>`;

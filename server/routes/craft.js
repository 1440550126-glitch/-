// LingCraft · 一句话生成：prompt → 单文件 HTML（游戏/页面/效果）→ 沙箱预览 / 分享。
// 铁律不变：大模型不可用时走本地模板兜底，零成本可跑通；生成物只进沙箱 iframe，绝不入主站上下文。
import { GET, POST, DEL, bad, notFound, denied } from '../lib/httpx.js';
import { q } from '../lib/db.js';
import { now, uid, sanitizeText } from '../lib/util.js';
import { isMember } from '../lib/auth.js';
import { resolveLLM, chatLLM, logUsage, useQuota, quotaUsed, userHasLLM } from '../lib/llm.js';

const FREE_GEN_PER_DAY = 8;
const MEMBER_GEN_PER_DAY = 80;
const UNLIMITED = 1_000_000;
const genLimit = (user) => (userHasLLM(user.id) ? UNLIMITED : isMember(user) ? MEMBER_GEN_PER_DAY : FREE_GEN_PER_DAY);

const row = (id) => q.get('SELECT * FROM craft_artifacts WHERE id = ?', Number(id));
const view = (a) => a && ({ id: a.id, title: a.title, prompt: a.prompt, by_llm: !!a.by_llm, share_id: a.share_id, created_at: a.created_at, updated_at: a.updated_at });

// 从模型输出里抠出完整 HTML 文档（容忍 ```html 围栏与前后解释文字）
export function extractHtml(text) {
  if (!text) return null;
  let t = String(text).trim();
  const fence = t.match(/```(?:html)?\s*([\s\S]*?)```/i);
  if (fence && /<html[\s>]|<!doctype/i.test(fence[1])) t = fence[1].trim();
  const i = t.search(/<!doctype\s+html|<html[\s>]/i);
  if (i < 0) return null;
  t = t.slice(i);
  const end = t.toLowerCase().lastIndexOf('</html>');
  if (end > 0) t = t.slice(0, end + 7);
  return t.length > 120 ? t : null;
}

// ---------------- 本地模板兜底（无大模型也能出可玩的东西） ----------------
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function tplSnake(title) {
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)}</title><style>body{margin:0;background:#0b0d12;color:#e8ecf5;font-family:system-ui;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh}
h1{font-size:18px;margin:10px}canvas{background:#11141c;border:1px solid #262c3a;border-radius:12px;touch-action:none}#s{color:#3ddc97;font-weight:700}</style></head>
<body><h1>${esc(title)} · 得分 <span id="s">0</span></h1><canvas id="c" width="320" height="320"></canvas>
<p style="color:#8b93a7;font-size:13px">方向键 / WASD / 触屏滑动控制 · 本地模板引擎生成（接入大模型后效果更佳）</p>
<script>const c=document.getElementById('c'),x=c.getContext('2d'),G=16,N=20;let s=[[10,10]],d=[1,0],f=[15,10],sc=0,t;
function put(){f=[Math.floor(Math.random()*N),Math.floor(Math.random()*N)]}
function step(){const h=[(s[0][0]+d[0]+N)%N,(s[0][1]+d[1]+N)%N];
if(s.some(p=>p[0]===h[0]&&p[1]===h[1])){clearInterval(t);x.fillStyle='#ff6b81';x.font='20px system-ui';x.fillText('游戏结束 · 点击重开',70,160);c.onclick=()=>location.reload();return}
s.unshift(h);if(h[0]===f[0]&&h[1]===f[1]){sc+=10;document.getElementById('s').textContent=sc;put()}else s.pop();
x.fillStyle='#11141c';x.fillRect(0,0,320,320);x.fillStyle='#3ddc97';s.forEach(p=>x.fillRect(p[0]*G+1,p[1]*G+1,G-2,G-2));x.fillStyle='#ffb454';x.fillRect(f[0]*G+3,f[1]*G+3,G-6,G-6)}
addEventListener('keydown',e=>{const m={ArrowUp:[0,-1],ArrowDown:[0,1],ArrowLeft:[-1,0],ArrowRight:[1,0],w:[0,-1],s:[0,1],a:[-1,0],d:[1,0]}[e.key];if(m&&(m[0]!==-d[0]||m[1]!==-d[1]))d=m});
let ts=null;c.addEventListener('touchstart',e=>ts=[e.touches[0].clientX,e.touches[0].clientY]);
c.addEventListener('touchend',e=>{if(!ts)return;const dx=e.changedTouches[0].clientX-ts[0],dy=e.changedTouches[0].clientY-ts[1];
const m=Math.abs(dx)>Math.abs(dy)?[dx>0?1:-1,0]:[0,dy>0?1:-1];if(m[0]!==-d[0]||m[1]!==-d[1])d=m;ts=null});
t=setInterval(step,120);</script></body></html>`;
}

function tplPage(title, prompt) {
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)}</title><style>*{box-sizing:border-box}body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;font-family:system-ui;color:#fff;
background:linear-gradient(-45deg,#1a2a6c,#2d1b69,#0f4c5c,#1a2a6c);background-size:400% 400%;animation:g 12s ease infinite}
@keyframes g{0%{background-position:0 50%}50%{background-position:100% 50%}100%{background-position:0 50%}}
.card{max-width:640px;padding:48px 36px;text-align:center}
h1{font-size:clamp(26px,5vw,44px);margin:0 0 14px;background:linear-gradient(135deg,#6ea8fe,#3ddc97);-webkit-background-clip:text;background-clip:text;color:transparent}
p{color:rgba(255,255,255,.75);line-height:1.8;margin:0 0 26px}
a{display:inline-block;padding:13px 30px;border-radius:12px;background:linear-gradient(135deg,#6ea8fe,#9b8cff);color:#fff;text-decoration:none;font-weight:700}
small{display:block;margin-top:30px;color:rgba(255,255,255,.4);font-size:12px}</style></head>
<body><div class="card"><h1>${esc(title)}</h1><p>${esc(prompt)}</p><a href="#">立即体验</a>
<small>本地模板引擎生成 · 接入大模型后可按你的描述深度定制</small></div></body></html>`;
}

export function localCraft(prompt) {
  const p = String(prompt || '');
  const title = sanitizeText(p, 24) || '我的作品';
  if (/蛇|snake|贪吃/i.test(p)) return tplSnake(title);
  return tplPage(title, p);
}

// ---------------- 大模型生成 ----------------
const SYS_GEN = `你是资深前端工程师。根据用户需求产出一个【完整、可独立运行的单文件 HTML】（游戏 / 页面 / 交互效果）。
硬性要求：
1. 只输出 HTML 代码，从 <!DOCTYPE html> 开始到 </html> 结束，不要任何解释文字；
2. 所有 CSS/JS 全部内联在这个文件里；禁止任何外部资源（无 CDN、无外链图片/字体/脚本、无 fetch/XHR）；
3. 移动端适配（viewport、触屏可用）；界面美观、深色系优先；
4. 若是游戏：可直接玩、有计分或反馈、键盘与触屏都能操作；
5. 代码健壮，不得抛未捕获异常。`;

async function llmCraft(userId, prompt, prevHtml, instruction) {
  const cfg = resolveLLM(userId);
  if (!cfg.enabled) return null;
  const user = prevHtml
    ? `这是当前作品的完整代码：\n\n${prevHtml.slice(0, 24000)}\n\n请按以下修改要求输出修改后的【完整单文件 HTML】（同样只输出代码）：\n${instruction}`
    : `需求：${prompt}`;
  const t0 = now();
  try {
    const r = await chatLLM({ tier: 'default', system: SYS_GEN, prompt: user, maxTokens: 4000, temperature: 0.75, timeoutMs: 60_000, cfg });
    logUsage({ userId, feature: 'craft_gen', provider: cfg.provider, model: r.model, promptTokens: r.promptTokens, completionTokens: r.completionTokens, ok: 1, latency: now() - t0 });
    return extractHtml(r.text);
  } catch (e) {
    logUsage({ userId, feature: 'craft_gen', provider: cfg.provider, model: '-', ok: 0, fallback: 1, latency: now() - t0 });
    console.warn('[craft] llm fallback:', e.message);
    return null;
  }
}

function gate(user) {
  if (!useQuota(user.id, 'craft_gen', genLimit(user))) {
    throw denied(
      isMember(user) ? '今天的生成额度用完了～自带大模型 Key 即可不限量' : `每天可免费生成 ${FREE_GEN_PER_DAY} 次，订阅会员或自带 Key 可提升`,
      { need_member: !isMember(user), quota_exceeded: true }
    );
  }
}

// ---------------- 路由 ----------------
POST('/api/craft/generate', async (ctx) => {
  const prompt = sanitizeText(ctx.body?.prompt, 600);
  if (!prompt) throw bad('先用一句话描述你想要什么');
  gate(ctx.user);
  const html = await llmCraft(ctx.user.id, prompt, null, null);
  const finalHtml = html || localCraft(prompt);
  const ts = now();
  const r = q.run(
    'INSERT INTO craft_artifacts (owner_id, title, prompt, html, by_llm, created_at, updated_at) VALUES (?,?,?,?,?,?,?)',
    ctx.user.id, sanitizeText(prompt, 40), prompt, finalHtml, html ? 1 : 0, ts, ts
  );
  return { artifact: view(row(Number(r.lastInsertRowid))) };
}, { auth: true });

POST('/api/craft/:id/revise', async (ctx) => {
  const a = row(ctx.params.id);
  if (!a || a.owner_id !== ctx.user.id) throw notFound();
  const instruction = sanitizeText(ctx.body?.instruction, 600);
  if (!instruction) throw bad('说说要怎么改');
  gate(ctx.user);
  const html = await llmCraft(ctx.user.id, a.prompt, a.html, instruction);
  if (!html) throw bad('这次修改没有生成有效代码（大模型不可用或输出异常），原作品未变，稍后再试');
  q.run('UPDATE craft_artifacts SET html = ?, prompt = ?, by_llm = 1, updated_at = ? WHERE id = ?', html, instruction, now(), a.id);
  return { artifact: view(row(a.id)) };
}, { auth: true });

GET('/api/craft/mine', async (ctx) => ({
  items: q.all('SELECT id, title, prompt, by_llm, share_id, created_at, updated_at FROM craft_artifacts WHERE owner_id = ? ORDER BY updated_at DESC LIMIT 50', ctx.user.id)
    .map((a) => ({ ...a, by_llm: !!a.by_llm })),
  quota: { used: quotaUsed(ctx.user.id, 'craft_gen'), limit: genLimit(ctx.user) }
}), { auth: true });

GET('/api/craft/:id', async (ctx) => {
  const a = row(ctx.params.id);
  if (!a || a.owner_id !== ctx.user.id) throw notFound();
  return { artifact: { ...view(a), html: a.html } };
}, { auth: true });

DEL('/api/craft/:id', async (ctx) => {
  const a = row(ctx.params.id);
  if (!a || a.owner_id !== ctx.user.id) throw notFound();
  q.run('DELETE FROM craft_artifacts WHERE id = ?', a.id);
  return { deleted: true };
}, { auth: true });

POST('/api/craft/:id/share', async (ctx) => {
  const a = row(ctx.params.id);
  if (!a || a.owner_id !== ctx.user.id) throw notFound();
  let sid = a.share_id;
  if (!sid) { sid = uid('c_', 12); q.run('UPDATE craft_artifacts SET share_id = ? WHERE id = ?', sid, a.id); }
  return { share_id: sid };
}, { auth: true });

DEL('/api/craft/:id/share', async (ctx) => {
  const a = row(ctx.params.id);
  if (!a || a.owner_id !== ctx.user.id) throw notFound();
  q.run('UPDATE craft_artifacts SET share_id = NULL WHERE id = ?', a.id);
  return { unshared: true };
}, { auth: true });

// —— 沙箱化原样输出：CSP sandbox（脚本可跑但成 opaque origin），并禁掉一切外联（connect/img 等仅 data:/blob:）——
function sendSandboxedHtml(ctx, html) {
  ctx.res.writeHead(200, {
    'Content-Type': 'text/html; charset=utf-8',
    'Content-Security-Policy': "sandbox allow-scripts allow-pointer-lock; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; media-src data: blob:; font-src data:; connect-src 'none'",
    'X-Content-Type-Options': 'nosniff',
    'Cache-Control': 'no-store'
  });
  ctx.res.end(html);
}

GET('/api/craft/:id/preview', async (ctx) => {   // iframe 用 ?token= 鉴权
  const a = row(ctx.params.id);
  if (!a || a.owner_id !== ctx.user.id) throw notFound();
  sendSandboxedHtml(ctx, a.html);
}, { auth: true });

GET('/api/public/craft/:shareId', async (ctx) => {  // 公开分享：免登录直接可玩
  const a = q.get('SELECT * FROM craft_artifacts WHERE share_id = ?', String(ctx.params.shareId));
  if (!a) throw notFound('分享不存在或已取消');
  sendSandboxedHtml(ctx, a.html);
});

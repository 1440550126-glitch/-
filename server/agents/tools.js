// 灵阵 · 工具/插件注册表
// 每个工具都是确定性的，无需大模型即可真实执行——所以本地引擎模式下团队照样能算数、查知识、抓网页。
// 工具形态：{ id, name, icon, desc, params, safe, run(args, ctx) -> { ok, result, data? } }
//   result：给智能体看的「观察」文本；data：可选结构化数据。
import { searchKnowledge } from './knowledge.js';
import { dayCN } from '../lib/util.js';

// ---- 安全计算器：递归下降解析，绝不用 eval ----
function calc(expr) {
  const s = String(expr).replace(/[，,]/g, '').replace(/×/g, '*').replace(/÷/g, '/').replace(/\s+/g, '');
  if (!/^[0-9+\-*/%.()^]+$/.test(s)) throw new Error('表达式含非法字符，只支持 + - * / % ^ ( ) 和数字');
  let i = 0;
  const peek = () => s[i];
  const eof = () => i >= s.length;
  function parseExpr() {            // + -
    let v = parseTerm();
    while (!eof() && (peek() === '+' || peek() === '-')) { const op = s[i++]; const r = parseTerm(); v = op === '+' ? v + r : v - r; }
    return v;
  }
  function parseTerm() {            // * / %
    let v = parsePow();
    while (!eof() && (peek() === '*' || peek() === '/' || peek() === '%')) {
      const op = s[i++]; const r = parsePow();
      if ((op === '/' || op === '%') && r === 0) throw new Error('除数为 0');
      v = op === '*' ? v * r : op === '/' ? v / r : v % r;
    }
    return v;
  }
  function parsePow() {             // ^ （右结合）
    const v = parseUnary();
    if (!eof() && peek() === '^') { i++; return Math.pow(v, parsePow()); }
    return v;
  }
  function parseUnary() {
    if (peek() === '+') { i++; return parseUnary(); }
    if (peek() === '-') { i++; return -parseUnary(); }
    return parseAtom();
  }
  function parseAtom() {
    if (peek() === '(') { i++; const v = parseExpr(); if (peek() !== ')') throw new Error('括号不匹配'); i++; return v; }
    let num = '';
    while (!eof() && /[0-9.]/.test(peek())) num += s[i++];
    if (!num) throw new Error('表达式不完整');
    return parseFloat(num);
  }
  const v = parseExpr();
  if (!eof()) throw new Error('表达式无法解析');
  if (!Number.isFinite(v)) throw new Error('结果不是有限数');
  return v;
}

// ---- web_fetch 的 SSRF 防护：禁止内网 / 本机 / 元数据地址 ----
function isBlockedHost(host) {
  const h = host.toLowerCase().replace(/^\[|\]$/g, '');
  if (['localhost', '0.0.0.0', '::1'].includes(h) || h.endsWith('.local') || h.endsWith('.internal')) return true;
  if (h === '169.254.169.254') return true; // 云元数据
  const m = h.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (m) {
    const [a, b] = [Number(m[1]), Number(m[2])];
    if (a === 127 || a === 10 || a === 0 || (a === 192 && b === 168) || (a === 172 && b >= 16 && b <= 31) || (a === 169 && b === 254)) return true;
  }
  return false;
}
function stripHtml(html) {
  return String(html)
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
    .replace(/\s+/g, ' ').trim();
}

export const TOOLS = {
  calculator: {
    id: 'calculator', name: '计算器', icon: '🧮', safe: true,
    desc: '精确计算数学表达式，支持 + - * / % ^ 和括号',
    params: { expression: '要计算的数学表达式，如 (1200*0.3+88)/12' },
    async run({ expression }) {
      if (!expression) return { ok: false, result: '缺少 expression 参数' };
      try { const v = calc(expression); return { ok: true, result: `${expression} = ${v}`, data: { value: v } }; }
      catch (e) { return { ok: false, result: `计算失败：${e.message}` }; }
    }
  },

  datetime: {
    id: 'datetime', name: '日期时间', icon: '🕑', safe: true,
    desc: '获取当前北京时间，或计算到某个日期还有多少天',
    params: { date: '可选，目标日期 YYYY-MM-DD，给出则计算与今天相差天数' },
    async run({ date }) {
      const nowTs = Date.now();
      const cn = new Date(nowTs + 8 * 3600_000);
      const week = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][cn.getUTCDay()];
      const today = dayCN();
      const hhmm = `${String(cn.getUTCHours()).padStart(2, '0')}:${String(cn.getUTCMinutes()).padStart(2, '0')}`;
      let result = `现在是北京时间 ${today} ${hhmm}（${week}）`;
      const data = { today, time: hhmm, week };
      if (date && /^\d{4}-\d{2}-\d{2}$/.test(date)) {
        const target = new Date(date + 'T00:00:00+08:00').getTime();
        const days = Math.round((target - new Date(today + 'T00:00:00+08:00').getTime()) / 86400_000);
        data.days_diff = days;
        result += `；距离 ${date} ${days === 0 ? '就是今天' : days > 0 ? `还有 ${days} 天` : `已过去 ${-days} 天`}`;
      }
      return { ok: true, result, data };
    }
  },

  text_stats: {
    id: 'text_stats', name: '文本统计', icon: '📏', safe: true,
    desc: '统计文本字数、中文字数、句子数与预计阅读时长',
    params: { text: '要统计的文本' },
    async run({ text }) {
      const t = String(text || '');
      if (!t) return { ok: false, result: '缺少 text 参数' };
      const chars = [...t].length;
      const noSpace = [...t.replace(/\s/g, '')].length;
      const cjk = (t.match(/[一-鿿]/g) || []).length;
      const latin = (t.match(/[a-zA-Z]+/g) || []).length;
      const sentences = (t.match(/[。！？!?]/g) || []).length || (t.trim() ? 1 : 0);
      const minutes = Math.max(1, Math.round((cjk + latin) / 350));
      const data = { chars, chars_no_space: noSpace, cjk, words_latin: latin, sentences, read_minutes: minutes };
      return { ok: true, result: `共 ${chars} 字符（不含空格 ${noSpace}），中文 ${cjk} 字、英文词 ${latin}、句子约 ${sentences} 句，预计阅读 ${minutes} 分钟`, data };
    }
  },

  knowledge_search: {
    id: 'knowledge_search', name: '知识库检索', icon: '📚', safe: true,
    desc: '在团队挂载的知识库里检索与问题最相关的资料片段（RAG）',
    params: { query: '检索关键词或问题', top_k: '可选，返回片段数，默认 4' },
    async run({ query, top_k }, ctx = {}) {
      if (!query) return { ok: false, result: '缺少 query 参数' };
      if (!ctx.kbIds?.length) return { ok: true, result: '（该团队未挂载知识库，无可检索资料）', data: { hits: [] } };
      const hits = searchKnowledge(ctx.kbIds, query, Math.min(8, Math.max(1, Number(top_k) || 4)));
      if (!hits.length) return { ok: true, result: `知识库中未找到与「${query}」相关的资料`, data: { hits: [] } };
      const result = hits.map((h, i) => `【片段${i + 1}·${h.source}】${h.text}`).join('\n');
      return { ok: true, result, data: { hits } };
    }
  },

  random_pick: {
    id: 'random_pick', name: '随机抽选', icon: '🎲', safe: true,
    desc: '从候选项里随机抽取若干个，或生成范围内随机整数（头脑风暴/抽样用）',
    params: { options: '候选项数组（与 min/max 二选一）', n: '抽取个数，默认 1', min: '随机整数下界', max: '随机整数上界' },
    async run({ options, n, min, max }) {
      if (Array.isArray(options) && options.length) {
        const k = Math.min(options.length, Math.max(1, Number(n) || 1));
        const a = [...options];
        for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
        const picked = a.slice(0, k);
        return { ok: true, result: `抽到：${picked.join('、')}`, data: { picked } };
      }
      if (min != null && max != null) {
        const lo = Math.min(Number(min), Number(max)), hi = Math.max(Number(min), Number(max));
        const v = lo + Math.floor(Math.random() * (hi - lo + 1));
        return { ok: true, result: `随机数（${lo}~${hi}）：${v}`, data: { value: v } };
      }
      return { ok: false, result: '需要提供 options 数组，或 min 与 max' };
    }
  },

  web_fetch: {
    id: 'web_fetch', name: '网页抓取', icon: '🌐', safe: false,
    desc: '抓取一个公开网页并提取正文文本（受部署网络策略限制，内网地址被禁止）',
    params: { url: '要抓取的 http/https 网址' },
    async run({ url }) {
      let u;
      try { u = new URL(String(url)); } catch { return { ok: false, result: '无效的网址' }; }
      if (!['http:', 'https:'].includes(u.protocol)) return { ok: false, result: '只支持 http/https' };
      if (isBlockedHost(u.hostname)) return { ok: false, result: '出于安全考虑，禁止抓取内网 / 本机 / 元数据地址' };
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 8000);
      try {
        const resp = await fetch(u.href, { signal: ctrl.signal, redirect: 'follow', headers: { 'User-Agent': 'LingArray-Agent/1.0' } });
        if (!resp.ok) return { ok: false, result: `抓取失败：HTTP ${resp.status}` };
        const ct = resp.headers.get('content-type') || '';
        const raw = (await resp.text()).slice(0, 200_000);
        const text = (ct.includes('html') ? stripHtml(raw) : raw).slice(0, 1500);
        return { ok: true, result: `来自 ${u.host} 的内容（已截断）：\n${text}`, data: { host: u.host, length: text.length } };
      } catch (e) {
        return { ok: false, result: `抓取失败（可能是网络策略限制或超时）：${e.message}` };
      } finally { clearTimeout(timer); }
    }
  }
};

export const toolList = () => Object.values(TOOLS).map(({ run, ...meta }) => meta);
export const getTool = (id) => TOOLS[id];
// 给智能体提示词用的工具清单
export function toolsSpec(ids = []) {
  return ids.map((id) => TOOLS[id]).filter(Boolean)
    .map((t) => `- ${t.id}（${t.name}）：${t.desc}。参数：${JSON.stringify(t.params)}`).join('\n');
}

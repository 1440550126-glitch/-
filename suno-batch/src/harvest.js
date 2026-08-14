// 自动下载生成的音频（best-effort）。
// 原理：监听页面网络响应，从 SUNO 前端轮询的 JSON 里捞出带 audio_url 的 clip（id/title/status），
// 记进清单；clip 出好后用带登录态的请求把 mp3 下到 var/downloads/。
// 注意：依赖 SUNO 内部接口形态，改版可能失效——失效时不影响主流程（生成照常），仅下载不到，
//       可退回手动在 SUNO 资料库里下载。
import { mkdirSync, existsSync, appendFileSync } from 'node:fs';
import { join } from 'node:path';
import { config } from './config.js';

const safe = s => String(s || 'untitled').replace(/[\\/:*?"<>|\n\r]+/g, '_').replace(/\s+/g, ' ').trim().slice(0, 60);

// 递归从任意 JSON 里找出形如 clip 的对象（有 id + audio_url）
export function collectClips(node, out) {
  if (!node || typeof node !== 'object') return;
  if (Array.isArray(node)) { for (const x of node) collectClips(x, out); return; }
  const id = node.id || node.clip_id;
  const url = node.audio_url || node.audioUrl;
  if (id && typeof url === 'string' && /^https?:\/\//.test(url)) {
    out.push({ id: String(id), audio_url: url, title: node.title || node.display_name || '', status: node.status || '' });
  }
  for (const k of Object.keys(node)) {
    const v = node[k];
    if (v && typeof v === 'object') collectClips(v, out);
  }
}

export function attachHarvest(context, page) {
  const dir = join(config.root, 'var', 'downloads');
  const manifest = join(config.root, 'var', 'downloads.jsonl');
  mkdirSync(dir, { recursive: true });
  const clips = new Map();       // id -> { audio_url, title, status }
  const downloaded = new Set();

  page.on('response', async (res) => {
    try {
      const ct = res.headers()['content-type'] || '';
      if (!ct.includes('application/json')) return;
      const url = res.url();
      if (!/suno|clip|feed|generate|song/i.test(url)) return; // 只看可能含歌曲数据的接口
      const body = await res.json().catch(() => null);
      if (!body) return;
      const found = [];
      collectClips(body, found);
      for (const c of found) {
        const prev = clips.get(c.id) || {};
        clips.set(c.id, { ...prev, ...c });
      }
    } catch { /* 忽略：不是所有响应都可解析 */ }
  });

  async function downloadOne(report, c) {
    if (downloaded.has(c.id) || !c.audio_url) return false;
    try {
      const resp = await context.request.get(c.audio_url, { timeout: 60_000 });
      if (!resp.ok()) return false;
      const buf = await resp.body();
      const file = join(dir, `${safe(c.title)}-${c.id.slice(0, 8)}.mp3`);
      const { writeFileSync } = await import('node:fs');
      writeFileSync(file, buf);
      downloaded.add(c.id);
      appendFileSync(manifest, JSON.stringify({ id: c.id, title: c.title, file, ts: new Date().toISOString() }) + '\n');
      report?.('download', { id: c.id, title: c.title, file });
      return true;
    } catch { return false; }
  }

  return {
    // 下载当前已就绪、尚未下载的 clip
    async flush(report) {
      for (const [, c] of clips) await downloadOne(report, c);
    },
    // 收尾：轮询等待仍在生成中的 clip 出好并下载，最长 waitMs
    async drain(report, waitMs = 4 * 60_000) {
      const end = Date.now() + waitMs;
      while (Date.now() < end) {
        let pending = 0;
        for (const [, c] of clips) if (!downloaded.has(c.id) && c.audio_url) await downloadOne(report, c);
        for (const [, c] of clips) if (!downloaded.has(c.id)) pending++;
        if (pending === 0 && clips.size > 0) break;
        await page.waitForTimeout(5000);
      }
      report?.('harvest-done', { total: downloaded.size });
    },
    stats: () => ({ seen: clips.size, downloaded: downloaded.size }),
  };
}

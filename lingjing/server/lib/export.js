// 灵境AI · 成片导出：按分镜顺序拼接 MP4（运行时检测 ffmpeg，无则友好提示）
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { UPLOAD_DIR } from './db.js';
import { uid, jparse } from './util.js';
import { bad } from './httpx.js';
import { getProject, getCanvas, addAsset, projectOut } from './pipeline.js';

let _ffmpeg = null;
export function ffmpegPath() {
  if (_ffmpeg !== null) return _ffmpeg;
  const bin = process.env.FFMPEG_PATH || 'ffmpeg';
  try {
    const r = spawnSync(bin, ['-version'], { stdio: 'ignore', timeout: 5000 });
    _ffmpeg = r.status === 0 ? bin : '';
  } catch { _ffmpeg = ''; }
  return _ffmpeg;
}

/** 抽取视频最后一帧为 PNG（视频接龙：上一段尾帧→下一段首帧）。返回 /uploads/xxx.png 或空。 */
export function extractLastFrame(videoUrl) {
  const ff = ffmpegPath();
  if (!ff) return '';
  // 本地文件优先；若仍是远端地址（落盘失败时），让 ffmpeg 直接读 http(s) 兜底
  const f = localFile(videoUrl) || (/^https?:\/\//i.test(videoUrl || '') ? videoUrl : null);
  if (!f) return '';
  const outName = `${uid('lf')}.png`;
  const outFile = path.join(UPLOAD_DIR, outName);
  // 从距结尾 0.15s 处取一帧（避免取到黑场尾）
  let r = spawnSync(ff, ['-y', '-sseof', '-0.15', '-i', f, '-update', '1', '-frames:v', '1', outFile], { stdio: 'ignore', timeout: 30000 });
  if (r.status !== 0 || !fs.existsSync(outFile)) {
    // 退路：直接取最后一帧
    r = spawnSync(ff, ['-y', '-i', f, '-vf', 'reverse', '-frames:v', '1', outFile], { stdio: 'ignore', timeout: 30000 });
  }
  return fs.existsSync(outFile) ? `/uploads/${outName}` : '';
}

function localFile(url) {
  if (!url?.startsWith('/uploads/')) return null;
  const f = path.normalize(path.join(UPLOAD_DIR, url.slice('/uploads/'.length)));
  return f.startsWith(UPLOAD_DIR) && fs.existsSync(f) ? f : null;
}

function run(bin, args, opts = {}) {
  return new Promise((resolve) => {
    const p = spawn(bin, args, { stdio: ['ignore', 'ignore', 'pipe'], ...opts });
    let err = '';
    p.stderr.on('data', (d) => { err += d; if (err.length > 8000) err = err.slice(-8000); });
    p.on('close', (code) => resolve({ code, err }));
    p.on('error', () => resolve({ code: -1, err: '启动 ffmpeg 失败' }));
  });
}

const srtTime = (sec) => {
  const ms = Math.round((sec % 1) * 1000), s = Math.floor(sec);
  const p = (n, w = 2) => String(n).padStart(w, '0');
  return `${p(Math.floor(s / 3600))}:${p(Math.floor(s / 60) % 60)}:${p(s % 60)},${p(ms, 3)}`;
};

/**
 * 导出成片：逐镜【混入配音 + 烧录字幕】后拼接（音画/字幕逐镜对齐，带容错）。
 * @param opts.subtitles 是否烧录字幕（默认 true） opts.dub 是否混入配音（默认 true）
 */
export async function exportEpisode({ projectId, episode = '', subtitles = true, dub = true }) {
  const project = getProject(projectId);
  const sb = jparse(project.storyboard, null);
  if (!sb?.shots?.length) throw bad('项目还没有分镜，先解析剧本');
  if (!project.canvas_id) throw bad('项目还没有画布');
  const ff = ffmpegPath();
  if (!ff) throw bad('未检测到 ffmpeg：安装后即可一键导出（macOS: brew install ffmpeg / Ubuntu: apt install ffmpeg），放映室连播预览不受影响');

  // 配音齐活：开了配音 + 已配置 TTS + 有台词镜头还没配音 → 先自动补配音，保证成片有声
  if (dub) {
    try {
      const { ttsEnabled } = await import('./tts.js');
      const { generateDubbing } = await import('./pipeline.js');
      if (ttsEnabled()) {
        const cv0 = getCanvas(project.canvas_id);
        const need = cv0.nodes.some((n) => n.type === 'shot' && n.data.dialogue?.trim() && !n.data.audio && (!episode || (n.data.episode || 'e1') === episode));
        if (need) { try { await generateDubbing({ projectId, episode }); } catch (e) { console.warn('[export] 自动配音跳过：', e.message); } }
      }
    } catch { /* noop */ }
  }

  const canvas = getCanvas(project.canvas_id);
  const byKey = new Map(canvas.nodes.filter((n) => n.data?.key).map((n) => [n.data.key, n]));
  const shots = sb.shots.filter((s) => !episode || (s.episode || 'e1') === episode);
  if (!shots.length) throw bad('该集没有分镜');

  // 收集每镜的视频/配音/台词
  const clips = [];
  const missing = [];
  for (const s of shots) {
    const n = byKey.get(s.key);
    const v = n?.data?.video || '';
    const f = /\.mp4$/i.test(v) ? localFile(v) : null;
    if (f) clips.push({ file: f, audio: dub ? localFile(n?.data?.audio || '') : null, text: (s.dialogue || '').trim(), order: s.order });
    else missing.push(`镜头${s.order}`);
  }
  if (missing.length) throw bad(`还有 ${missing.length} 个分镜没有可拼接的 MP4（${missing.slice(0, 6).join('、')}${missing.length > 6 ? '…' : ''}）。请先生成真实视频`);

  // 逐镜处理：烧字幕 + 混配音（在 UPLOAD_DIR 内作业，规避字幕滤镜路径转义问题）
  const processed = [];
  const tmp = [];
  let dubbed = 0, subbed = 0;
  const STYLE = "force_style='Fontsize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,Outline=2,Shadow=0,Alignment=2,MarginV=28'";
  for (let i = 0; i < clips.length; i++) {
    const c = clips[i];
    const base = path.basename(c.file);
    const outName = `${uid('seg')}.mp4`;
    const vf = [];
    let srtName = '';
    if (subtitles && c.text) {
      srtName = `${uid('s')}.srt`;
      fs.writeFileSync(path.join(UPLOAD_DIR, srtName), `1\n${srtTime(0)} --> ${srtTime(60)}\n${c.text}\n`);
      vf.push(`subtitles=${srtName}:${STYLE}`);
    }
    const args = ['-y', '-i', base];
    if (c.audio) args.push('-i', path.basename(c.audio));
    if (vf.length) args.push('-vf', vf.join(','));
    if (c.audio) {
      // 视频时长为准：音频补静音再裁齐（-shortest）
      args.push('-map', '0:v:0', '-map', '1:a:0', '-af', 'apad', '-shortest', '-c:a', 'aac');
    } else {
      args.push('-c:a', 'aac');   // 保留原声道（多为静音）
    }
    args.push('-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-r', '24', outName);
    const r = await run(ff, args, { cwd: UPLOAD_DIR });
    if (srtName) tmp.push(path.join(UPLOAD_DIR, srtName));
    if (r.code === 0 && fs.existsSync(path.join(UPLOAD_DIR, outName))) {
      processed.push(path.join(UPLOAD_DIR, outName));
      tmp.push(path.join(UPLOAD_DIR, outName));
      if (c.audio) dubbed++;
      if (srtName) subbed++;
    } else {
      processed.push(c.file);   // 处理失败 → 退回原片（无字幕/配音）
    }
  }

  // 拼接（已统一编码，concat 重编码确保兼容）
  const listFile = path.join(UPLOAD_DIR, `${uid('cc')}.txt`);
  fs.writeFileSync(listFile, processed.map((f) => `file '${f.replace(/'/g, `'\\''`)}'`).join('\n'));
  tmp.push(listFile);
  const outName = `${uid('cut')}.mp4`;
  const outFile = path.join(UPLOAD_DIR, outName);
  let r = await run(ff, ['-y', '-f', 'concat', '-safe', '0', '-i', listFile, '-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-c:a', 'aac', outFile]);
  if (r.code !== 0) r = await run(ff, ['-y', '-f', 'concat', '-safe', '0', '-i', listFile, '-c', 'copy', outFile]);
  for (const t of tmp) { try { fs.rmSync(t, { force: true }); } catch { /* noop */ } }
  if (r.code !== 0) throw bad('ffmpeg 拼接失败：' + r.err.split('\n').slice(-3).join(' ').slice(0, 300));

  const epTitle = episode ? (sb.episodes?.find((e) => e.key === episode)?.title || episode) : '全片';
  const asset = addAsset({
    tab: 'material', kind: 'video', name: `成片·${project.title}·${epTitle}`,
    url: `/uploads/${outName}`, prompt: '', source: 'local', projectId: project.id
  });
  return { url: `/uploads/${outName}`, asset_id: asset.id, shots: clips.length, dubbed, subbed, project: projectOut(getProject(projectId)) };
}

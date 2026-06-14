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
  const f = localFile(videoUrl);
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

function run(bin, args) {
  return new Promise((resolve) => {
    const p = spawn(bin, args, { stdio: ['ignore', 'ignore', 'pipe'] });
    let err = '';
    p.stderr.on('data', (d) => { err += d; if (err.length > 8000) err = err.slice(-8000); });
    p.on('close', (code) => resolve({ code, err }));
    p.on('error', () => resolve({ code: -1, err: '启动 ffmpeg 失败' }));
  });
}

/** 导出项目（或其中一集）的成片：按分镜顺序拼接已生成的 MP4 */
export async function exportEpisode({ projectId, episode = '' }) {
  const project = getProject(projectId);
  const sb = jparse(project.storyboard, null);
  if (!sb?.shots?.length) throw bad('项目还没有分镜，先解析剧本');
  if (!project.canvas_id) throw bad('项目还没有画布');

  if (!ffmpegPath()) {
    throw bad('未检测到 ffmpeg：安装后即可一键导出成片（macOS: brew install ffmpeg / Ubuntu: apt install ffmpeg），放映室连播预览不受影响');
  }

  const canvas = getCanvas(project.canvas_id);
  const byKey = new Map(canvas.nodes.filter((n) => n.data?.key).map((n) => [n.data.key, n]));
  const shots = sb.shots.filter((s) => !episode || (s.episode || 'e1') === episode);
  if (!shots.length) throw bad('该集没有分镜');

  const files = [];
  const missing = [];
  for (const s of shots) {
    const v = byKey.get(s.key)?.data?.video || '';
    const f = /\.mp4$/i.test(v) ? localFile(v) : null;
    if (f) files.push(f);
    else missing.push(`镜头${s.order}`);
  }
  if (missing.length) {
    throw bad(`还有 ${missing.length} 个分镜没有可拼接的 MP4（${missing.slice(0, 6).join('、')}${missing.length > 6 ? '…' : ''}）。本地预览片不能导出，请接入方舟生成真实视频后再试`);
  }

  const listFile = path.join(UPLOAD_DIR, `${uid('cc')}.txt`);
  fs.writeFileSync(listFile, files.map((f) => `file '${f.replace(/'/g, `'\\''`)}'`).join('\n'));
  const outName = `${uid('cut')}.mp4`;
  const outFile = path.join(UPLOAD_DIR, outName);

  // 同源片段直接流拷贝；失败再重编码一次
  let r = await run(ffmpegPath(), ['-y', '-f', 'concat', '-safe', '0', '-i', listFile, '-c', 'copy', outFile]);
  if (r.code !== 0) {
    r = await run(ffmpegPath(), ['-y', '-f', 'concat', '-safe', '0', '-i', listFile,
      '-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-c:a', 'aac', outFile]);
  }
  fs.rmSync(listFile, { force: true });
  if (r.code !== 0) throw bad('ffmpeg 拼接失败：' + r.err.split('\n').slice(-3).join(' ').slice(0, 300));

  const epTitle = episode ? (sb.episodes?.find((e) => e.key === episode)?.title || episode) : '全片';
  const asset = addAsset({
    tab: 'material', kind: 'video', name: `成片·${project.title}·${epTitle}`,
    url: `/uploads/${outName}`, prompt: '', source: 'local', projectId: project.id
  });
  return { url: `/uploads/${outName}`, asset_id: asset.id, shots: files.length, project: projectOut(getProject(projectId)) };
}

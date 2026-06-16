// dolby-player Demo：播放列表 / 传输控制 / 进度 / 杜比音效 / 湍流可视化
import { DolbyPlayer } from './dolby-player.js';
import { DOLBY_PRESETS, presetById } from './dolby-audio.js';
import { coverColor } from './dolby-visualizer.js';
import { createVisualizer } from './dolby-visualizer-gl.js';

const $ = (id) => document.getElementById(id);
const el = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
const fmt = (s) => { if (!isFinite(s) || s < 0) return '0:00'; s = Math.floor(s); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };

const player = new DolbyPlayer({
  tracks: [
    { src: 'demo-assets/track-1.wav', title: '潮汐 · Am–F–C–G', artist: 'dolby-audio demo', album: 'dolby-audio' },
    { src: 'demo-assets/track-2.wav', title: '夜行 · Dm–B♭–F–C', artist: 'dolby-audio demo', album: 'dolby-audio' }
  ],
  dolby: { preset: 'music', analyser: true }
});
const dolby = player.dolby;

// —— 湍流可视化背景（WebGL 流体优先，失败回退 Canvas2D；跟随节奏 + 随频谱/封面变色） ——
const viz = createVisualizer($('viz'), { dolby, particles: 120 });
let vizStarted = false;
const HUES = [275, 205, 330, 150];
// 没有真实封面时，按曲目生成一张程序化封面（也用于喂进 WebGL 背景纹理）
function makeCover(track, index) {
  const c = document.createElement('canvas'); c.width = c.height = 256;
  const x = c.getContext('2d'), hue = HUES[index % HUES.length];
  const g = x.createLinearGradient(0, 0, 256, 256);
  g.addColorStop(0, `hsl(${hue},70%,55%)`); g.addColorStop(1, `hsl(${(hue + 60) % 360},65%,32%)`);
  x.fillStyle = g; x.fillRect(0, 0, 256, 256);
  x.globalAlpha = 0.22; x.fillStyle = '#fff';
  for (let i = 0; i < 6; i++) { x.beginPath(); x.arc(Math.random() * 256, Math.random() * 256, 20 + Math.random() * 70, 0, Math.PI * 2); x.fill(); }
  x.globalAlpha = 1;
  const title = (track && typeof track === 'object' && track.title) ? track.title : '♪';
  x.fillStyle = 'rgba(255,255,255,.92)'; x.font = 'bold 130px sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
  x.fillText([...title][0] || '♪', 128, 132);
  return c;
}
function applyTheme(track, index) {
  const apply = (src, hue) => { if (viz.setCover) viz.setCover(src); viz.setBaseHue(hue); document.documentElement.style.setProperty('--hue', String(Math.round(hue))); };
  const cover = track && typeof track === 'object' ? track.cover : null;
  const fallback = () => { const cv = makeCover(track, index); let h = HUES[index % HUES.length]; try { h = coverColor(cv).hue; } catch { /* ok */ } apply(cv, h); };
  if (cover) { const img = new Image(); img.crossOrigin = 'anonymous'; img.onload = () => { let h = HUES[index % HUES.length]; try { h = coverColor(img).hue; } catch { /* ok */ } apply(img, h); }; img.onerror = fallback; img.src = cover; }
  else fallback();
}

// —— 现在播放 + 进度 ——
const seek = $('seek'); let seeking = false;
player.on('track', ({ index, track }) => { $('title').textContent = track.title || track.src; $('artist').textContent = track.artist || ''; renderList(); applyTheme(track, index); });
player.on('time', ({ currentTime, duration }) => {
  $('cur').textContent = fmt(currentTime); $('dur').textContent = fmt(duration);
  if (!seeking && duration) seek.value = Math.round(currentTime / duration * 1000);
});
player.on('loaded', ({ duration }) => { $('dur').textContent = fmt(duration); });
player.on('play', () => { $('play').textContent = '⏸'; if (!vizStarted) { vizStarted = true; viz.start(); } });
player.on('pause', () => { $('play').textContent = '▶'; });
player.on('error', () => { $('plHint').textContent = '该音频无法播放（可能是浏览器 CSP 限制了 blob: 媒体）。'; });

seek.addEventListener('input', () => { seeking = true; });
seek.addEventListener('change', () => { const d = player.duration; if (d) player.seek(seek.value / 1000 * d); seeking = false; });

// —— 传输 ——
$('play').addEventListener('click', () => player.toggle());
$('prev').addEventListener('click', () => player.prev(player.playing));
$('next').addEventListener('click', () => player.next(player.playing));
const shuffleBtn = $('shuffle');
shuffleBtn.addEventListener('click', () => { player.setShuffle(!player.shuffle); shuffleBtn.classList.toggle('on', player.shuffle); });
const repeatBtn = $('repeat'), REPEAT = ['off', 'all', 'one'], ICON = { off: '🔁', all: '🔁', one: '🔂' };
repeatBtn.addEventListener('click', () => {
  player.setRepeat(REPEAT[(REPEAT.indexOf(player.repeat) + 1) % REPEAT.length]);
  repeatBtn.textContent = ICON[player.repeat]; repeatBtn.classList.toggle('on', player.repeat !== 'off');
});
$('vol').addEventListener('input', () => player.setVolume($('vol').value / 100));

// —— 播放列表 ——
function renderList() {
  const pl = $('playlist'); pl.innerHTML = '';
  player.tracks.forEach((t, i) => {
    const title = typeof t === 'string' ? t : (t.title || t.src);
    const artist = typeof t === 'string' ? '' : (t.artist || '');
    const box = el('div'); box.style.flex = '1'; box.append(el('div', '', title));
    if (artist) box.append(el('div', 'ar', artist));
    const item = el('div', 'pl-item' + (i === player.index ? ' active' : ''));
    item.append(el('span', 'idx', String(i + 1)), box);
    item.addEventListener('click', () => player.load(i, true));
    pl.append(item);
  });
}
$('file').addEventListener('change', (e) => {
  const files = [...e.target.files];
  for (const f of files) player.add({ src: URL.createObjectURL(f), title: f.name, artist: '本地文件' });
  renderList();
  if (files.length) $('plHint').textContent = `已添加 ${files.length} 个本地文件到列表末尾，点击即可播放。`;
});

// —— 杜比音效 ——
const swEl = $('dolbySwitch'), stateEl = $('dolbyState');
function refreshDolby() { stateEl.textContent = `${dolby.enabled ? '已开启' : '已关闭（原声）'} · ${presetById(dolby.presetId).label}`; swEl.classList.toggle('on', dolby.enabled); }
swEl.addEventListener('click', () => { dolby.setEnabled(!dolby.enabled); refreshDolby(); });
const presetsEl = $('presets');
DOLBY_PRESETS.forEach((p) => {
  const b = el('button', 'chip' + (p.id === dolby.presetId ? ' active' : ''), p.label); b.title = p.desc;
  b.addEventListener('click', () => { dolby.setEnabled(true); dolby.setPreset(p.id); [...presetsEl.children].forEach((c) => c.classList.toggle('active', c === b)); refreshDolby(); });
  presetsEl.append(b);
});
const hpEl = $('hpSwitch');
hpEl.addEventListener('click', () => { const on = dolby.spatialMode !== 'headphones'; dolby.setSpatialMode(on ? 'headphones' : 'speakers'); hpEl.classList.toggle('on', on); });
$('intensity').addEventListener('input', () => dolby.setIntensity($('intensity').value / 100));

// —— 初始化 UI ——
renderList();
const cur = player.current;
$('title').textContent = cur ? (cur.title || cur.src) : '—';
$('artist').textContent = cur ? (cur.artist || '') : '';
refreshDolby();
applyTheme(cur, Math.max(0, player.index));
setInterval(() => { const b = viz.last.bpm; $('bpm').textContent = b ? `· ${b} BPM` : ''; }, 400);

// —— 沉浸全屏 ——
$('fs').addEventListener('click', () => {
  const el = document.documentElement;
  if (!document.fullscreenElement) {
    (el.requestFullscreen || el.webkitRequestFullscreen || (() => {})).call(el);
    document.body.classList.add('immersive');
  } else {
    (document.exitFullscreen || document.webkitExitFullscreen || (() => {})).call(document);
    document.body.classList.remove('immersive');
  }
});
document.addEventListener('fullscreenchange', () => { if (!document.fullscreenElement) document.body.classList.remove('immersive'); });

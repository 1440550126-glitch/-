// dolby-audio Demo：内置合成音乐 + 文件 A/B + 频谱可视化 + 均衡曲线
import { DolbyAudio, DOLBY_PRESETS, presetById, registerPreset } from './dolby-audio.js';
import { DolbyABTest } from './dolby-abtest.js';
import { exportPresets, importPresets } from './dolby-store.js';

const $ = (id) => document.getElementById(id);
const clampN = (v, a, b) => Math.min(b, Math.max(a, v));

// —— 引擎（带分析器，懒唤醒；先建好以便调参与可视化）——
const dolby = new DolbyAudio({ analyser: true, preset: 'standard', intensity: 0.85 });
const ctx = dolby.context;
const mix = ctx.createGain(); mix.gain.value = 0.85;     // 总混音母线 → 引擎
dolby.attachSource(mix);
const synthBus = ctx.createGain(); synthBus.connect(mix);
const fileBus = ctx.createGain(); fileBus.connect(mix);

let mode = 'synth', playing = false, synthTimer = null, step = 0, fileBuf = null, fileSrc = null;

// —— 合成音乐：Am–F–C–G 循环（铺底 pad + 低音 + 琶音，立体声声像）——
const CH = [
  { notes: [220.0, 261.63, 329.63], bass: 110.0 },   // Am
  { notes: [174.61, 220.0, 261.63], bass: 87.31 },   // F
  { notes: [261.63, 329.63, 392.0], bass: 130.81 },  // C
  { notes: [196.0, 246.94, 293.66], bass: 98.0 }     // G
];
function pan(p) { const n = ctx.createStereoPanner(); n.pan.value = p; return n; }
function padVoice(f, t0, dur, p) {
  for (const det of [-6, 6]) {
    const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = f; o.detune.value = det;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 1800;
    const g = ctx.createGain(); g.gain.setValueAtTime(0, t0);
    g.gain.linearRampToValueAtTime(0.09, t0 + 0.45);
    g.gain.setTargetAtTime(0.0001, t0 + dur * 0.7, 0.4);
    o.connect(lp); lp.connect(g); g.connect(pan(p)).connect(synthBus);
    o.start(t0); o.stop(t0 + dur + 0.3);
  }
}
function bassVoice(f, t0, dur) {
  const o = ctx.createOscillator(); o.type = 'sine'; o.frequency.value = f;
  const g = ctx.createGain(); g.gain.setValueAtTime(0, t0);
  g.gain.linearRampToValueAtTime(0.32, t0 + 0.04);
  g.gain.setTargetAtTime(0.0001, t0 + dur * 0.55, 0.35);
  o.connect(g); g.connect(synthBus);
  o.start(t0); o.stop(t0 + dur + 0.2);
}
function arpVoice(f, t0, p) {
  const o = ctx.createOscillator(); o.type = 'triangle'; o.frequency.value = f;
  const g = ctx.createGain(); g.gain.setValueAtTime(0, t0);
  g.gain.linearRampToValueAtTime(0.16, t0 + 0.01);
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.32);
  o.connect(g); g.connect(pan(p)).connect(synthBus);
  o.start(t0); o.stop(t0 + 0.4);
}
function scheduleChord() {
  const c = CH[step % CH.length], t0 = ctx.currentTime + 0.02, dur = 2.0;
  c.notes.forEach((f, i) => padVoice(f, t0, dur, (i - 1) * 0.45));
  bassVoice(c.bass, t0, dur);
  for (let k = 0; k < 8; k++) {
    const f = c.notes[k % c.notes.length] * (k >= 4 ? 2 : 1);
    arpVoice(f, t0 + k * 0.25, k % 2 ? 0.6 : -0.6);
  }
  step++;
}

async function start() {
  await dolby.resume();
  playing = true; $('play').textContent = '⏸ 暂停';
  if (mode === 'synth') { scheduleChord(); synthTimer = setInterval(scheduleChord, 2000); }
  else if (fileBuf) playFile();
}
function stop() {
  playing = false; $('play').textContent = '▶ 试听' + (mode === 'file' ? '文件' : '合成音乐');
  if (synthTimer) { clearInterval(synthTimer); synthTimer = null; }
  if (fileSrc) { try { fileSrc.stop(); } catch { /* ok */ } fileSrc = null; }
}
function playFile() {
  if (fileSrc) { try { fileSrc.stop(); } catch { /* ok */ } }
  fileSrc = ctx.createBufferSource(); fileSrc.buffer = fileBuf; fileSrc.loop = true;
  fileSrc.connect(fileBus); fileSrc.start();
}

$('play').addEventListener('click', () => (playing ? stop() : start()));

$('file').addEventListener('change', async (e) => {
  const f = e.target.files[0]; if (!f) return;
  try {
    const buf = await f.arrayBuffer();
    fileBuf = await ctx.decodeAudioData(buf);   // 不走网络/blob，规避严格 CSP
    mode = 'file'; $('srcHint').textContent = `已载入：${f.name} · 循环播放`;
    if (synthTimer) { clearInterval(synthTimer); synthTimer = null; }
    await dolby.resume(); playing = true; $('play').textContent = '⏸ 暂停'; playFile();
  } catch { $('srcHint').textContent = '无法解码该音频文件，换一个试试（建议 mp3/wav/m4a）。'; }
});

// —— 杜比开关 ——
const swEl = $('dolbySwitch'), stateEl = $('dolbyState');
function refreshState() {
  const p = presetById(dolby.presetId);
  stateEl.textContent = `${dolby.enabled ? '已开启' : '已关闭（原声）'} · ${p.label}`;
  swEl.classList.toggle('on', dolby.enabled);
}
swEl.addEventListener('click', () => { dolby.setEnabled(!dolby.enabled); refreshState(); });

// —— 耳机 HRTF 虚拟环绕 ——
const hpEl = $('hpSwitch');
hpEl.addEventListener('click', () => {
  const on = dolby.spatialMode !== 'headphones';
  dolby.setSpatialMode(on ? 'headphones' : 'speakers');
  hpEl.classList.toggle('on', on);
});
// —— 多频带压缩 / 响度对齐 ——
const mbEl = $('mbSwitch');
mbEl.addEventListener('click', () => { const on = !dolby.multiband; dolby.setMultiband(on); mbEl.classList.toggle('on', on); });
const lmEl = $('lmSwitch');
lmEl.addEventListener('click', () => { const on = !dolby.loudnessMatch; dolby.setLoudnessMatch(on); lmEl.classList.toggle('on', on); });

// —— 按住听原声（A/B 即时对比） ——
const abEl = $('abHold'); let abPrev = null;
const abDown = (e) => { e.preventDefault(); abPrev = dolby.enabled; dolby.setEnabled(false); abEl.classList.add('primary'); abEl.textContent = '正在听原声…松开恢复'; };
const abUp = () => { if (abPrev === null) return; dolby.setEnabled(abPrev); abPrev = null; abEl.classList.remove('primary'); abEl.textContent = '按住听原声 (A/B)'; refreshState(); };
abEl.addEventListener('pointerdown', abDown);
for (const ev of ['pointerup', 'pointerleave', 'pointercancel']) abEl.addEventListener(ev, abUp);

// —— 预设 ——
const presetsEl = $('presets');
DOLBY_PRESETS.forEach((p) => {
  const b = document.createElement('button');
  b.className = 'chip' + (p.id === dolby.presetId ? ' active' : '');
  b.textContent = p.label; b.title = p.desc;
  b.addEventListener('click', () => {
    dolby.setEnabled(true); dolby.setPreset(p.id);
    [...presetsEl.children].forEach((c) => c.classList.toggle('active', c === b));
    syncSliders(p.p); refreshState(); drawEq();
  });
  presetsEl.append(b);
});

// —— 滑杆 ——
const I = $('intensity'), W = $('width'), B = $('bass'), R = $('reverb'), A = $('air'), V = $('vocal');
function syncSliders(p) {
  W.value = Math.round(p.width * 100); $('widthV').textContent = (p.width).toFixed(2) + '×';
  B.value = Math.round(p.bass.gain); $('bassV').textContent = `+${Math.round(p.bass.gain)}dB`;
  R.value = Math.round(p.reverb.mix * 100); $('reverbV').textContent = Math.round(p.reverb.mix * 100) + '%';
  A.value = Math.round(p.air.gain); $('airV').textContent = `+${Math.round(p.air.gain)}dB`;
  V.value = Math.round(p.vocal || 0); $('vocalV').textContent = `+${Math.round(p.vocal || 0)}dB`;
}
I.addEventListener('input', () => { dolby.setIntensity(I.value / 100); $('intensityV').textContent = I.value + '%'; });
W.addEventListener('input', () => { const v = W.value / 100; dolby.setWidth(v); $('widthV').textContent = v.toFixed(2) + '×'; });
B.addEventListener('input', () => { dolby.setBass(+B.value); $('bassV').textContent = `+${B.value}dB`; drawEq(); });
R.addEventListener('input', () => { dolby.setReverb(R.value / 100); $('reverbV').textContent = R.value + '%'; });
A.addEventListener('input', () => { dolby.setAir(+A.value); $('airV').textContent = `+${A.value}dB`; drawEq(); });
V.addEventListener('input', () => { dolby.setVocal(+V.value); $('vocalV').textContent = `+${V.value}dB`; });

// —— 频谱可视化 + 输出电平表 ——
const cvs = $('viz'), cc = cvs.getContext('2d'), analyser = dolby.getAnalyser(), meterFill = $('meterFill');
const bins = analyser.frequencyBinCount, data = new Uint8Array(bins);
function resize() { const dpr = Math.min(devicePixelRatio || 1, 2); cvs.width = cvs.clientWidth * dpr; cvs.height = 120 * dpr; cc.setTransform(dpr, 0, 0, dpr, 0, 0); }
resize(); addEventListener('resize', resize);
function draw() {
  requestAnimationFrame(draw);
  analyser.getByteFrequencyData(data);
  const w = cvs.clientWidth, h = 120; cc.clearRect(0, 0, w, h);
  const n = 56, step2 = Math.floor(bins / n);
  const grad = cc.createLinearGradient(0, 0, w, 0);
  grad.addColorStop(0, '#a18bff'); grad.addColorStop(1, '#ff9ec6');
  cc.fillStyle = grad;
  for (let i = 0; i < n; i++) {
    const v = data[i * step2] / 255, bh = Math.max(2, v * h * 0.95);
    const bw = w / n;
    cc.fillRect(i * bw + 1, h - bh, bw - 2, bh);
  }
  meterFill.style.width = Math.min(100, dolby.getLevel().peak * 130) + '%';
}
draw();

// —— 可拖拽图形均衡 ——
const eqC = $('eq'), eqCtx = eqC.getContext('2d'), EQH = 120, EQR = 12;
const LMIN = Math.log10(20), LMAX = Math.log10(20000);
const xOf = (freq, w) => (Math.log10(freq) - LMIN) / (LMAX - LMIN) * w;
const yOf = (g, h) => h / 2 - clampN(g, -EQR, EQR) / EQR * (h / 2 - 14);
function resizeEq() { const dpr = Math.min(devicePixelRatio || 1, 2); eqC.width = eqC.clientWidth * dpr; eqC.height = EQH * dpr; eqCtx.setTransform(dpr, 0, 0, dpr, 0, 0); }
function drawEq() {
  const w = eqC.clientWidth, h = EQH; eqCtx.clearRect(0, 0, w, h);
  eqCtx.strokeStyle = 'rgba(255,255,255,.14)'; eqCtx.lineWidth = 1;
  eqCtx.beginPath(); eqCtx.moveTo(0, h / 2); eqCtx.lineTo(w, h / 2); eqCtx.stroke();
  const { magDb } = dolby.getFrequencyResponse(), n = magDb.length;
  const grad = eqCtx.createLinearGradient(0, 0, w, 0); grad.addColorStop(0, '#a18bff'); grad.addColorStop(1, '#ff9ec6');
  eqCtx.strokeStyle = grad; eqCtx.lineWidth = 2; eqCtx.beginPath();
  for (let i = 0; i < n; i++) { const x = i / (n - 1) * w, y = yOf(magDb[i], h); i ? eqCtx.lineTo(x, y) : eqCtx.moveTo(x, y); }
  eqCtx.stroke();
  eqCtx.fillStyle = '#fff';
  for (const b of dolby.getEQ()) { eqCtx.beginPath(); eqCtx.arc(xOf(b.freq, w), yOf(b.gain, h), 6, 0, Math.PI * 2); eqCtx.fill(); }
}
addEventListener('resize', () => { resizeEq(); drawEq(); });
resizeEq();
// 拖拽各频段
let dragIdx = -1;
const eqPt = (e) => { const r = eqC.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top, w: r.width, h: r.height }; };
function eqMove(e) {
  if (dragIdx < 0) return;
  const p = eqPt(e), g = clampN((p.h / 2 - p.y) / (p.h / 2 - 14) * EQR, -EQR, EQR);
  dolby.setEQBand(dragIdx, Math.round(g * 10) / 10, true); drawEq();
}
eqC.addEventListener('pointerdown', (e) => {
  const p = eqPt(e); let best = -1, bd = 24;
  dolby.getEQ().forEach((b, i) => { const dx = Math.abs(xOf(b.freq, p.w) - p.x); if (dx < bd) { bd = dx; best = i; } });
  if (best >= 0) { dragIdx = best; eqC.setPointerCapture(e.pointerId); e.preventDefault(); eqMove(e); }
});
eqC.addEventListener('pointermove', eqMove);
for (const ev of ['pointerup', 'pointercancel', 'pointerleave']) eqC.addEventListener(ev, () => { dragIdx = -1; });
$('eqReset').addEventListener('click', () => { dolby.resetEQ(); drawEq(); });
const customPresets = []; let customN = 0;
function addCustomChip(preset, activate = true) {
  const b = document.createElement('button'); b.className = 'chip' + (activate ? ' active' : ''); b.textContent = preset.label; b.title = '我保存的预设';
  b.addEventListener('click', () => { dolby.setEnabled(true); dolby.setPreset(preset.id); [...presetsEl.children].forEach((c) => c.classList.toggle('active', c === b)); syncSliders(presetById(preset.id).p); refreshState(); drawEq(); });
  if (activate) [...presetsEl.children].forEach((c) => c.classList.remove('active'));
  presetsEl.append(b); if (activate) refreshState();
}
$('eqSave').addEventListener('click', () => {
  customN++;
  const preset = dolby.snapshotPreset('custom-' + customN, '自定义 ' + customN);
  registerPreset(preset); customPresets.push(preset); addCustomChip(preset);
});
const ioBox = $('ioBox');
$('pExport').addEventListener('click', () => {
  ioBox.style.display = 'block';
  ioBox.value = exportPresets(customPresets.length ? customPresets : [dolby.snapshotPreset('current', '当前设置')]);
});
$('pImport').addEventListener('click', () => {
  if (ioBox.style.display === 'none' || !ioBox.value.trim()) { ioBox.style.display = 'block'; ioBox.placeholder = '粘贴预设 JSON 后，再点一次「导入预设」'; return; }
  try {
    const arr = importPresets(ioBox.value);
    for (const p of arr) { registerPreset(p); customPresets.push(p); addCustomChip(p, false); }
    ioBox.value = `已导入 ${arr.length} 个预设 ✅（在预设区可点选）`;
  } catch (e) { ioBox.value = '导入失败：' + e.message; }
});

refreshState();
drawEq();

// —— A/B 盲测打分 ——
const ab = new DolbyABTest(dolby); ab.newRound();
const abResult = $('abResult'), abStats = $('abStats');
function abShowStats() { const s = ab.stats; abStats.textContent = s.rounds ? `已 ${s.rounds} 轮 · 偏好增强 ${Math.round(s.rate * 100)}%（${s.preferEnhanced}/${s.rounds}）` : '还没有数据'; }
$('abA').addEventListener('click', () => { ab.audition('A'); abResult.textContent = '🔊 正在听 A…（再点「听 B」对比）'; });
$('abB').addEventListener('click', () => { ab.audition('B'); abResult.textContent = '🔊 正在听 B…'; });
function abPick(slot) {
  const r = ab.choose(slot);
  abResult.textContent = `你选了 ${slot}，增强其实在 ${r.enhancedSlot} —— ${r.pickedEnhanced ? '✅ 你更喜欢杜比增强' : '🅰 你更喜欢原声'}`;
  abShowStats(); refreshState(); ab.newRound();
}
$('abPickA').addEventListener('click', () => abPick('A'));
$('abPickB').addEventListener('click', () => abPick('B'));
$('abNext').addEventListener('click', () => { ab.newRound(); abResult.textContent = '新一轮：先听听 A 和 B'; });
abShowStats();

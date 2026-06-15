// dolby-audio Demo：内置合成音乐 + 文件 A/B + 频谱可视化
import { DolbyAudio, DOLBY_PRESETS, presetById } from './dolby-audio.js';

const $ = (id) => document.getElementById(id);

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

// —— 预设 ——
const presetsEl = $('presets');
DOLBY_PRESETS.forEach((p) => {
  const b = document.createElement('button');
  b.className = 'chip' + (p.id === dolby.presetId ? ' active' : '');
  b.textContent = p.label; b.title = p.desc;
  b.addEventListener('click', () => {
    dolby.setEnabled(true); dolby.setPreset(p.id);
    [...presetsEl.children].forEach((c) => c.classList.toggle('active', c === b));
    syncSliders(p.p); refreshState();
  });
  presetsEl.append(b);
});

// —— 滑杆 ——
const I = $('intensity'), W = $('width'), B = $('bass'), R = $('reverb'), A = $('air');
function syncSliders(p) {
  W.value = Math.round(p.width * 100); $('widthV').textContent = (p.width).toFixed(2) + '×';
  B.value = Math.round(p.bass.gain); $('bassV').textContent = `+${Math.round(p.bass.gain)}dB`;
  R.value = Math.round(p.reverb.mix * 100); $('reverbV').textContent = Math.round(p.reverb.mix * 100) + '%';
  A.value = Math.round(p.air.gain); $('airV').textContent = `+${Math.round(p.air.gain)}dB`;
}
I.addEventListener('input', () => { dolby.setIntensity(I.value / 100); $('intensityV').textContent = I.value + '%'; });
W.addEventListener('input', () => { const v = W.value / 100; dolby.setWidth(v); $('widthV').textContent = v.toFixed(2) + '×'; });
B.addEventListener('input', () => { dolby.setBass(+B.value); $('bassV').textContent = `+${B.value}dB`; });
R.addEventListener('input', () => { dolby.setReverb(R.value / 100); $('reverbV').textContent = R.value + '%'; });
A.addEventListener('input', () => { dolby.setAir(+A.value); $('airV').textContent = `+${A.value}dB`; });

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
refreshState();

// 声音引擎：Web Audio 实时合成（无音频文件依赖）
// 环境音（风/雨/海浪/夜/火）+ 单发音效（钟音/嗖/心跳/碎裂/脚步/呼噜…）
let ctx = null;
let noiseBuf = null;

const midiToFreq = (m) => 440 * Math.pow(2, (m - 69) / 12);

function ac() {
  if (!ctx) {
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    const len = ctx.sampleRate * 2;
    noiseBuf = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = noiseBuf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
  }
  if (ctx.state === 'suspended') ctx.resume();
  return ctx;
}

function noiseSrc() {
  const s = ac().createBufferSource();
  s.buffer = noiseBuf;
  s.loop = true;
  return s;
}

export class SoundScape {
  constructor() {
    this.master = ac().createGain();
    this.master.gain.value = 0.6;
    this.master.connect(ac().destination);
    this.live = [];       // 活动节点（stop 时统一断开）
    this.timers = [];
    this.muted = false;
  }
  setVolume(v) { this.master.gain.setTargetAtTime(this.muted ? 0 : v, ac().currentTime, 0.2); this._vol = v; }
  toggleMute() {
    this.muted = !this.muted;
    this.master.gain.setTargetAtTime(this.muted ? 0 : (this._vol ?? 0.6), ac().currentTime, 0.1);
    return this.muted;
  }

  _keep(...nodes) { this.live.push(...nodes); }
  _timer(fn, ms) { const t = setTimeout(fn, ms); this.timers.push(t); return t; }

  // ---- 环境音 ----
  ambient(name, vol = 0.5) {
    const t = ac().currentTime;
    if (name === 'wind') {
      const src = noiseSrc();
      const lp = ac().createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 380; lp.Q.value = 0.4;
      const g = ac().createGain(); g.gain.value = 0;
      g.gain.setTargetAtTime(vol * 0.5, t, 1.2);
      const lfo = ac().createOscillator(); lfo.frequency.value = 0.13;
      const lfoG = ac().createGain(); lfoG.gain.value = vol * 0.18;
      lfo.connect(lfoG); lfoG.connect(g.gain);
      src.connect(lp); lp.connect(g); g.connect(this.master);
      src.start(); lfo.start();
      this._keep(src, lfo, g);
    } else if (name === 'rain') {
      const src = noiseSrc();
      const bp = ac().createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 2400; bp.Q.value = 0.5;
      const g = ac().createGain(); g.gain.value = 0;
      g.gain.setTargetAtTime(vol * 0.30, t, 1.0);
      src.connect(bp); bp.connect(g); g.connect(this.master);
      src.start();
      this._keep(src, g);
      const drop = () => {
        this.oneshot('droplet', vol * 0.5);
        this._timer(drop, 240 + Math.random() * 900);
      };
      this._timer(drop, 500);
    } else if (name === 'waves') {
      const src = noiseSrc();
      const lp = ac().createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 520;
      const g = ac().createGain(); g.gain.value = 0;
      g.gain.setTargetAtTime(vol * 0.4, t, 1.5);
      const lfo = ac().createOscillator(); lfo.frequency.value = 0.085;
      const lfoG = ac().createGain(); lfoG.gain.value = vol * 0.3;
      lfo.connect(lfoG); lfoG.connect(g.gain);
      src.connect(lp); lp.connect(g); g.connect(this.master);
      src.start(); lfo.start();
      this._keep(src, lfo, g);
    } else if (name === 'night') {
      const chirp = () => {
        for (let i = 0; i < 3; i++) {
          this._timer(() => this._pip(4150 + Math.random() * 250, 0.045, vol * 0.16), i * 110);
        }
        this._timer(chirp, 1400 + Math.random() * 2600);
      };
      this._timer(chirp, 800);
    } else if (name === 'fire') {
      const crackle = () => {
        this.oneshot('crackle', vol * 0.5);
        this._timer(crackle, 120 + Math.random() * 480);
      };
      this._timer(crackle, 300);
      const src = noiseSrc();
      const lp = ac().createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 240;
      const g = ac().createGain(); g.gain.value = vol * 0.12;
      src.connect(lp); lp.connect(g); g.connect(this.master);
      src.start();
      this._keep(src, g);
    }
  }

  _pip(freq, dur, vol) {
    const t = ac().currentTime;
    const o = ac().createOscillator(); o.frequency.value = freq;
    const g = ac().createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(vol, t + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(this.master);
    o.start(t); o.stop(t + dur + 0.05);
  }

  // ---- 单发音效 ----
  oneshot(name, vol = 0.5) {
    const t = ac().currentTime;
    if (name === 'chime') {
      [880, 1318.5, 1760].forEach((f, i) => {
        const o = ac().createOscillator(); o.frequency.value = f;
        const g = ac().createGain();
        g.gain.setValueAtTime(0, t + i * 0.05);
        g.gain.linearRampToValueAtTime(vol * 0.22 / (i + 1), t + i * 0.05 + 0.012);
        g.gain.exponentialRampToValueAtTime(0.0001, t + i * 0.05 + 1.4);
        o.connect(g); g.connect(this.master);
        o.start(t + i * 0.05); o.stop(t + 2);
      });
    } else if (name === 'swoosh') {
      const src = noiseSrc();
      const bp = ac().createBiquadFilter(); bp.type = 'bandpass'; bp.Q.value = 1.2;
      bp.frequency.setValueAtTime(280, t);
      bp.frequency.exponentialRampToValueAtTime(2800, t + 0.55);
      const g = ac().createGain();
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(vol * 0.4, t + 0.12);
      g.gain.exponentialRampToValueAtTime(0.0001, t + 0.7);
      src.connect(bp); bp.connect(g); g.connect(this.master);
      src.start(t); src.stop(t + 0.8);
    } else if (name === 'heartbeat') {
      [0, 0.34].forEach((dt, i) => {
        const o = ac().createOscillator(); o.frequency.setValueAtTime(58, t + dt);
        o.frequency.exponentialRampToValueAtTime(40, t + dt + 0.16);
        const g = ac().createGain();
        g.gain.setValueAtTime(0, t + dt);
        g.gain.linearRampToValueAtTime(vol * (i ? 0.5 : 0.7), t + dt + 0.015);
        g.gain.exponentialRampToValueAtTime(0.0001, t + dt + 0.22);
        o.connect(g); g.connect(this.master);
        o.start(t + dt); o.stop(t + dt + 0.3);
      });
    } else if (name === 'crack') {
      const src = noiseSrc();
      const hp = ac().createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 1400;
      const g = ac().createGain();
      g.gain.setValueAtTime(vol * 0.55, t);
      g.gain.exponentialRampToValueAtTime(0.0001, t + 0.28);
      src.connect(hp); hp.connect(g); g.connect(this.master);
      src.start(t); src.stop(t + 0.3);
      const o = ac().createOscillator(); o.type = 'triangle';
      o.frequency.setValueAtTime(420, t);
      o.frequency.exponentialRampToValueAtTime(90, t + 0.3);
      const g2 = ac().createGain();
      g2.gain.setValueAtTime(vol * 0.25, t);
      g2.gain.exponentialRampToValueAtTime(0.0001, t + 0.35);
      o.connect(g2); g2.connect(this.master);
      o.start(t); o.stop(t + 0.4);
    } else if (name === 'pop' || name === 'droplet') {
      const o = ac().createOscillator();
      o.frequency.setValueAtTime(name === 'pop' ? 520 : 1150 + Math.random() * 600, t);
      o.frequency.exponentialRampToValueAtTime(name === 'pop' ? 880 : 600, t + 0.08);
      const g = ac().createGain();
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(vol * 0.2, t + 0.008);
      g.gain.exponentialRampToValueAtTime(0.0001, t + 0.12);
      o.connect(g); g.connect(this.master);
      o.start(t); o.stop(t + 0.15);
    } else if (name === 'crackle') {
      const src = noiseSrc();
      const bp = ac().createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 800 + Math.random() * 2200; bp.Q.value = 2;
      const g = ac().createGain();
      g.gain.setValueAtTime(vol * 0.3, t);
      g.gain.exponentialRampToValueAtTime(0.0001, t + 0.05 + Math.random() * 0.06);
      src.connect(bp); bp.connect(g); g.connect(this.master);
      src.start(t); src.stop(t + 0.15);
    } else if (name === 'steps') {
      for (let i = 0; i < 4; i++) {
        const dt = i * 0.42;
        const o = ac().createOscillator(); o.frequency.value = 95;
        const g = ac().createGain();
        g.gain.setValueAtTime(0, t + dt);
        g.gain.linearRampToValueAtTime(vol * 0.18, t + dt + 0.01);
        g.gain.exponentialRampToValueAtTime(0.0001, t + dt + 0.1);
        o.connect(g); g.connect(this.master);
        o.start(t + dt); o.stop(t + dt + 0.15);
      }
    } else if (name === 'purr') {
      const o = ac().createOscillator(); o.type = 'sawtooth'; o.frequency.value = 27;
      const g = ac().createGain();
      const lfo = ac().createOscillator(); lfo.frequency.value = 11;
      const lg = ac().createGain(); lg.gain.value = vol * 0.10;
      lfo.connect(lg); lg.connect(g.gain);
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(vol * 0.16, t + 0.2);
      g.gain.setTargetAtTime(0.0001, t + 1.1, 0.2);
      o.connect(g); g.connect(this.master);
      o.start(t); lfo.start(t);
      o.stop(t + 1.8); lfo.stop(t + 1.8);
    } else if (name === 'wind' || name === 'rain' || name === 'waves' || name === 'night' || name === 'fire') {
      this.ambient(name, vol);     // timeline 里偶尔直接引用环境音名
    }
  }

  // ---- 一句话变一首歌：演唱 Song Manifest（主旋律 + 和弦铺底） ----
  // onNote(note,i) 在每个字唱响时回调（用于歌词逐字点亮）；onEnd 在唱完后回调。
  playMelody(song, { onNote, onEnd } = {}) {
    const A = ac();
    const t0 = A.currentTime + 0.15;
    const spb = 60 / (song.bpm || 90);          // 每拍秒数
    const inst = song.instrument || 'bell';

    // 和弦柔和铺底
    for (const ch of song.chords || []) {
      const when = t0 + ch.t * spb;
      for (const m of ch.midi || []) this._pad(midiToFreq(m), when, ch.dur * spb, 0.045);
    }

    // 主旋律"演唱"
    let lastEnd = t0;
    (song.melody || []).forEach((note, i) => {
      const when = t0 + note.t * spb;
      const dur = Math.max(0.12, note.dur * spb * 0.92);
      this._voice(midiToFreq(note.midi), when, dur, inst);
      lastEnd = Math.max(lastEnd, when + dur);
      if (onNote) this._timer(() => onNote(note, i), Math.max(0, (when - A.currentTime) * 1000));
    });
    if (onEnd) this._timer(onEnd, Math.max(0, (lastEnd - A.currentTime) * 1000 + 260));
    return lastEnd - t0;
  }

  // 单个"嗓音"音符：双振荡器 + 颤音 + ADSR 包络
  _voice(freq, when, dur, inst) {
    const A = ac();
    const types = { music_box: 'sine', soft_pluck: 'triangle', warm_pad: 'sine', bell: 'triangle' };
    const o = A.createOscillator(); o.type = types[inst] || 'triangle';
    const o2 = A.createOscillator(); o2.type = 'sine';        // 叠高八度泛音让音色更暖
    o.frequency.setValueAtTime(freq, when);
    o2.frequency.setValueAtTime(freq * 2, when);
    const o2g = A.createGain(); o2g.gain.value = 0.16;
    // 颤音（vibrato）：让长音更像"唱"
    const vib = A.createOscillator(); vib.frequency.value = 5.2;
    const vibG = A.createGain(); vibG.gain.value = freq * 0.006;
    vib.connect(vibG); vibG.connect(o.frequency);
    const g = A.createGain();
    const peak = 0.2;
    const atk = inst === 'soft_pluck' || inst === 'bell' ? 0.006 : 0.04;
    const rel = inst === 'warm_pad' ? 0.4 : 0.18;
    g.gain.setValueAtTime(0, when);
    g.gain.linearRampToValueAtTime(peak, when + atk);
    g.gain.setTargetAtTime(peak * 0.68, when + atk, 0.12);    // decay → sustain
    g.gain.setTargetAtTime(0.0001, when + dur, rel * 0.4);    // release
    o.connect(g); o2.connect(o2g); o2g.connect(g); g.connect(this.master);
    const end = when + dur + rel + 0.1;
    o.start(when); o2.start(when); vib.start(when);
    o.stop(end); o2.stop(end); vib.stop(end);
    this._keep(o, o2, vib, g);
  }

  // 柔和和弦铺底（低通 + 轻微失谐更厚）
  _pad(freq, when, dur, vol) {
    const A = ac();
    const o = A.createOscillator(); o.type = 'sine';
    const o2 = A.createOscillator(); o2.type = 'triangle';
    o.frequency.setValueAtTime(freq, when);
    o2.frequency.setValueAtTime(freq * 1.005, when);
    const lp = A.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 1400;
    const g = A.createGain();
    g.gain.setValueAtTime(0, when);
    g.gain.linearRampToValueAtTime(vol, when + 0.25);
    g.gain.setTargetAtTime(0.0001, when + Math.max(0.2, dur - 0.2), 0.18);
    o.connect(lp); o2.connect(lp); lp.connect(g); g.connect(this.master);
    const end = when + dur + 0.3;
    o.start(when); o2.start(when);
    o.stop(end); o2.stop(end);
    this._keep(o, o2, g);
  }

  stop() {
    for (const tm of this.timers) clearTimeout(tm);
    this.timers = [];
    const t = ac().currentTime;
    this.master.gain.setTargetAtTime(0.0001, t, 0.25);
    setTimeout(() => {
      for (const n of this.live) { try { n.stop?.(); } catch { /* ok */ } try { n.disconnect?.(); } catch { /* ok */ } }
      try { this.master.disconnect(); } catch { /* ok */ }
      this.live = [];
    }, 600);
  }
}
